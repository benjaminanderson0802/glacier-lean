// In-memory mock of the Glacier core v0 backend contract (docs/CONTRACT.md), for UI work and e2e tests.
// Usage: node mock/mock_server.mjs [port]   (default 8787, or env MOCK_PORT)
// Commands are NOT executed: a command's output is "$ <cmd>" plus a fake line; its exit code is 1 when the
// command text contains "fail" or "exit 1", else 0. Each node step takes STEP_MS (default 250ms).
import http from 'node:http'
import crypto from 'node:crypto'
import { WebSocketServer } from 'ws'

const PORT = Number(process.argv[2] ?? process.env.MOCK_PORT ?? 8787)
const STEP_MS = Number(process.env.STEP_MS ?? 250)
const MAX_EXEC = 50

const envs = new Map() // id -> Environment
const runs = new Map() // run_id -> run record
const vault = new Map() // path -> body
const sleep = ms => new Promise(r => setTimeout(r, ms))
const commitId = () => crypto.randomBytes(20).toString('hex').slice(0, 7)

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x')
  const send = (code, body) => {
    res.writeHead(code, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(body))
  }
  const readBody = () => new Promise(r => {
    let s = ''
    req.on('data', c => (s += c))
    req.on('end', () => { try { r(s ? JSON.parse(s) : {}) } catch { r(null) } })
  })
  const p = url.pathname
  let m
  try {
    if (req.method === 'GET' && p === '/api/environments') return send(200, [...envs.values()].map(e => ({ id: e.id, name: e.name })))
    if ((m = p.match(/^\/api\/environments\/([^/]+)$/))) {
      const id = decodeURIComponent(m[1])
      if (req.method === 'GET') return envs.has(id) ? send(200, envs.get(id)) : send(404, { detail: 'environment not found' })
      if (req.method === 'PUT') {
        const body = await readBody()
        if (!body || !Array.isArray(body.nodes) || !Array.isArray(body.edges)) return send(422, { detail: 'invalid environment' })
        envs.set(id, { ...body, id })
        const commit = commitId()
        vault.set(`environments/${id}.json`, JSON.stringify({ ...body, id }, null, 2))
        return send(200, { saved: true, commit })
      }
    }
    if (req.method === 'POST' && (m = p.match(/^\/api\/environments\/([^/]+)\/run$/))) {
      const id = decodeURIComponent(m[1])
      if (!envs.has(id)) return send(404, { detail: 'environment not found' })
      return send(200, { run_id: startRun(envs.get(id)) })
    }
    if (req.method === 'GET' && p === '/api/runs') {
      const envId = url.searchParams.get('env_id')
      const list = [...runs.values()].filter(r => !envId || r.env_id === envId)
        .sort((a, b) => b.started_at.localeCompare(a.started_at))
        .map(r => ({ run_id: r.run_id, env_id: r.env_id, status: r.status, started_at: r.started_at }))
      return send(200, list)
    }
    if (req.method === 'GET' && (m = p.match(/^\/api\/runs\/([^/]+)$/))) {
      const r = runs.get(decodeURIComponent(m[1]))
      return r ? send(200, publicRun(r)) : send(404, { detail: 'run not found' })
    }
    if (req.method === 'POST' && (m = p.match(/^\/api\/runs\/([^/]+)\/approve$/))) {
      const r = runs.get(decodeURIComponent(m[1]))
      if (!r) return send(404, { detail: 'run not found' })
      const body = await readBody()
      if (!body || r.waiting_on !== body.node_id || !r.resolve) return send(409, { detail: 'run is not waiting on that node' })
      r.resolve(body.approved === true)
      return send(200, { ok: true })
    }
    if (req.method === 'GET' && p === '/api/vault/notes') return send(200, [...vault.keys()].sort())
    if (req.method === 'GET' && p === '/api/vault/note') {
      const path = url.searchParams.get('path')
      return vault.has(path) ? send(200, { path, body: vault.get(path) }) : send(404, { detail: 'note not found' })
    }
    send(404, { detail: 'not found' })
  } catch (e) {
    send(500, { detail: String(e) })
  }
})

const wss = new WebSocketServer({ noServer: true })
server.on('upgrade', (req, sock, head) => {
  if (new URL(req.url, 'http://x').pathname !== '/api/events') return sock.destroy()
  wss.handleUpgrade(req, sock, head, ws => wss.emit('connection', ws, req))
})
const broadcast = msg => { const s = JSON.stringify(msg); for (const c of wss.clients) if (c.readyState === 1) c.send(s) }

function publicRun(r) {
  return { run_id: r.run_id, env_id: r.env_id, status: r.status, node_states: r.node_states, outputs: r.outputs, waiting_on: r.waiting_on }
}

function setState(r, nodeId, state, output) {
  r.node_states[nodeId] = state
  if (output !== undefined) r.outputs[nodeId] = output
  broadcast({ run_id: r.run_id, env_id: r.env_id, node_id: nodeId, state, ...(output !== undefined ? { output } : {}) })
}

function startRun(env) {
  const run_id = `run-${crypto.randomBytes(4).toString('hex')}`
  const r = {
    run_id, env_id: env.id, status: 'running', started_at: new Date().toISOString(),
    node_states: Object.fromEntries(env.nodes.map(n => [n.id, 'pending'])), outputs: {}, waiting_on: null, resolve: null,
  }
  runs.set(run_id, r)
  execute(structuredClone(env), r).catch(e => { r.status = 'failed'; console.error(e) })
  return run_id
}

function fill(tpl, vars) { return String(tpl ?? '').replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : `{${k}}`)) }

async function execute(env, r) {
  await sleep(150)
  const byId = new Map(env.nodes.map(n => [n.id, n]))
  const out = id => env.edges.filter(e => e.source === id)
  const targeted = new Set(env.edges.map(e => e.target))
  const starts = env.nodes.filter(n => n.type === 'schedule')
  const queue = (starts.length ? starts : env.nodes.filter(n => !targeted.has(n.id))).map(n => ({ id: n.id, prev: null }))
  let execs = 0
  let failed = false
  const summary = []
  while (queue.length && execs < MAX_EXEC) {
    const { id, prev } = queue.shift()
    const node = byId.get(id)
    if (!node) continue
    execs++
    setState(r, id, 'running')
    await sleep(STEP_MS)
    const c = node.config ?? {}
    let result = { exit_code: 0 }
    let next = out(id).filter(e => !e.label)
    switch (node.type) {
      case 'schedule':
        setState(r, id, 'done', `schedule ${c.cron ?? ''}\n`)
        break
      case 'command': {
        const code = /fail|exit 1/.test(c.cmd ?? '') ? 1 : 0
        const text = `$ ${c.cmd ?? ''}${c.cwd ? `   (cwd ${c.cwd})` : ''}\n${code ? 'mock: command failed' : `mock output of: ${c.cmd}`}\nexit code ${code}\n`
        result = { exit_code: code, output: text }
        summary.push(`${id} exit ${code}`)
        setState(r, id, code ? 'failed' : 'done', text)
        if (code) failed = true
        break
      }
      case 'check': {
        const ctx = prev ?? { exit_code: 0, output: '' }
        let ok = false
        try { ok = !!Function('exit_code', 'output', `return (${c.expr || 'false'})`)(ctx.exit_code, ctx.output ?? '') } catch { ok = false }
        result = ctx
        setState(r, id, 'done', `check ${c.expr} -> ${ok ? 'yes' : 'no'}\n`)
        next = out(id).filter(e => e.label === (ok ? 'yes' : 'no'))
        break
      }
      case 'approval': {
        r.status = 'waiting'; r.waiting_on = id
        setState(r, id, 'waiting', `waiting for approval: ${c.prompt ?? ''}\n`)
        const approved = await new Promise(res => { r.resolve = res })
        r.resolve = null; r.waiting_on = null; r.status = 'running'
        setState(r, id, 'done', `waiting for approval: ${c.prompt ?? ''}\n${approved ? 'approved' : 'rejected'}\n`)
        next = out(id).filter(e => e.label === (approved ? 'yes' : 'no'))
        if (!approved && next.length === 0) { r.status = 'rejected'; markSkipped(r); return }
        result = prev ?? result
        break
      }
      case 'note': {
        const path = fill(c.path || 'runs/{env}-{run}.md', { env: env.id, run: r.run_id })
        const body = fill(c.template || '', { env: env.id, run: r.run_id, summary: summary.join(', ') || 'ok' })
        vault.set(path, body)
        setState(r, id, 'done', `wrote ${path}\n${body}\n`)
        break
      }
      default:
        setState(r, id, 'failed', `unknown node type ${node.type}\n`)
        failed = true
    }
    for (const e of next) queue.push({ id: e.target, prev: result })
  }
  r.status = failed ? 'failed' : 'done'
  markSkipped(r)
  // the contract has no run-level event; a final state-less event would be ambiguous, so we just stop here.
}

function markSkipped(r) {
  for (const [id, s] of Object.entries(r.node_states)) if (s === 'pending') setState(r, id, 'skipped')
}

server.listen(PORT, () => console.log(`glacier mock api on http://localhost:${PORT}`))
