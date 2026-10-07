// In-memory mock of the Glacier core v0 backend contract (docs/CONTRACT.md), for UI work and e2e tests.
// Usage: node mock/mock_server.mjs [port]   (default 8787, or env MOCK_PORT)
// Commands are NOT executed: a command's output is "$ <cmd>" plus a fake line; its exit code is 1 when the
// command text contains "fail" or "exit 1", else 0. A codex node's output is "codex: <prompt>". Each node step takes STEP_MS (default 250ms).
import http from 'node:http'
import crypto from 'node:crypto'
import { WebSocketServer } from 'ws'
import { readFileSync } from 'node:fs'

// same node-type catalog the real backend serves
const CATALOG = JSON.parse(readFileSync(new URL('../../contract/node_types.json', import.meta.url), 'utf8')).types

const PORT = Number(process.argv[2] ?? process.env.MOCK_PORT ?? 8787)
const STEP_MS = Number(process.env.STEP_MS ?? 250)
const MAX_EXEC = 500
const MAX_DEPTH = 5
const MAX_LOOP = 1000

const envs = new Map() // id -> Environment
const runs = new Map() // run_id -> run record
const vault = new Map() // path -> body
const memoryMeta = new Map()
const memoryHistory = new Map()
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
    if (p.startsWith('/api/memory/')) {
      const clean = path => String(path ?? '').replace(/\.md$/, '')
      const parse = path => {
        const text = vault.get(path) ?? ''
        const title = (text.match(/^#\s+(.+)$/m) ?? [])[1] ?? path.split('/').pop().replace(/\.md$/, '')
        const tags = [...new Set([...text.matchAll(/(?:^|\s)#([\w-]+)/g)].map(x => x[1]))]
        return { title, author: memoryMeta.get(path)?.author ?? 'owner', run_id: memoryMeta.get(path)?.run_id ?? '',
          created: memoryMeta.get(path)?.created ?? new Date().toISOString(), updated: memoryMeta.get(path)?.updated ?? new Date().toISOString(), tags }
      }
      const links = body => [...new Set([...body.matchAll(/\[\[([^\]]+)\]\]/g)].map(x => clean(x[1].split('|', 1)[0].trim())))]
      if (req.method === 'GET' && p === '/api/memory/notes') {
        return send(200, [...vault.keys()].filter(x => x.endsWith('.md')).map(path => ({ path, ...parse(path) }))
          .filter(n => (!url.searchParams.get('tag') || n.tags.includes(url.searchParams.get('tag')))
            && (!url.searchParams.get('author') || n.author === url.searchParams.get('author'))))
      }
      if (req.method === 'GET' && p === '/api/memory/note') {
        const path = url.searchParams.get('path')
        if (!vault.has(path)) return send(404, { detail: 'Note not found' })
        const body = vault.get(path)
        return send(200, { path, body, meta: parse(path), links_out: links(body),
          links_in: [...vault].filter(([other, text]) => other !== path && links(text).includes(clean(path))).map(([other]) => clean(other)) })
      }
      if (req.method === 'PUT' && p === '/api/memory/note') {
        const item = await readBody()
        const normalise = value => {
          const raw = String(value ?? '').replaceAll('\\', '/')
          const parts = []
          for (const part of raw.split('/')) {
            if (!part || part === '.') continue
            if (part === '..') return null
            parts.push(part)
          }
          return parts.join('/')
        }
        if (!item || !item.path) return send(400, { detail: 'That note path is not allowed' })
        const path = normalise(item.path)
        if (!path || !path.endsWith('.md')) return send(400, { detail: 'That note path is not allowed' })
        if (path === 'claims.md' || path.startsWith('claims/')) return send(400, { detail: "Claims can't be edited from memory" })
        if (item.author !== 'owner') return send(400, { detail: 'Notes saved from the screen must be authored by owner' })
        if (Object.hasOwn(item, 'run_id')) return send(400, { detail: 'Run id is set by the service' })
        const change = vault.has(path) ? 'updated' : 'created'
        const oldMeta = memoryMeta.get(path)
        const now = new Date().toISOString()
        const title = (item.body.match(/^#\s+(.+)$/m) ?? [])[1] ?? path.split('/').pop().replace(/\.md$/, '')
        const tags = [...new Set([...item.body.matchAll(/(?:^|\s)#([\w-]+)/g)].map(x => x[1]))]
        vault.set(path, item.body); memoryMeta.set(path, { title, author: item.author, run_id: '', created: oldMeta?.created ?? now, updated: now, tags })
        const commit = commitId(), history = memoryHistory.get(path) ?? []
        history.unshift({ commit, author: item.author, date: now, message: `[${item.author}] write ${path}`, body: item.body }); memoryHistory.set(path, history)
        broadcast({ type: 'memory', path, change, author: item.author, run_id: '' })
        return send(200, { path, commit })
      }
      if (req.method === 'GET' && p === '/api/memory/graph') {
        const nodes = new Map(), edges = [], knownEdges = new Set()
        const edge = item => { const key = `${item.source}\0${item.target}\0${item.kind}`; if (!knownEdges.has(key)) { knownEdges.add(key); edges.push(item) } }
        for (const [path, body] of vault) if (path.endsWith('.md')) {
          const id = clean(path), meta = parse(path); nodes.set(id, { id, title: meta.title, kind: 'note', author: meta.author })
          edge({ source: id, target: meta.author, kind: 'wrote' })
          for (const target of links(body)) {
            if (!nodes.has(target)) nodes.set(target, { id: target, title: target.split('/').pop(), kind: target.startsWith('runs/') ? 'run' : target.startsWith('claims/') ? 'claim' : target.startsWith('flows/') || target.startsWith('environments/') ? 'flow' : 'note', author: '' })
            edge({ source: id, target, kind: 'link' })
          }
        }
        return send(200, { nodes: [...nodes.values()], edges })
      }
      if (req.method === 'GET' && p === '/api/memory/history') return send(200, memoryHistory.get(url.searchParams.get('path')) ?? [])
      if (req.method === 'POST' && p === '/api/memory/undo') {
        const item = await readBody()
        const path = String(item?.path ?? '').replaceAll('\\', '/').split('/').filter(x => x && x !== '.').join('/')
        if (!path.endsWith('.md')) return send(400, { detail: 'That note path is not allowed' })
        if (path === 'claims.md' || path.startsWith('claims/')) return send(400, { detail: "Claims can't be edited from memory" })
        const history = memoryHistory.get(path) ?? []
        const index = item.commit ? history.findIndex(row => row.commit.startsWith(item.commit)) : 0
        if (index < 0 || !history[index + 1]) return send(404, { detail: 'No earlier version exists' })
        const old = history[index + 1]; vault.set(path, old.body); history.splice(0, index + 1); memoryHistory.set(path, history)
        const commit = commitId(); history.unshift({ ...old, commit });
        broadcast({ type: 'memory', path, change: 'updated', author: 'owner', run_id: '' })
        return send(200, { path, commit })
      }
      if (req.method === 'GET' && p === '/api/memory/search') {
        const q = (url.searchParams.get('q') ?? '').toLowerCase(), mode = url.searchParams.get('mode')
        const fallback = mode === 'meaning'
        return send(200, [...vault].filter(([path, body]) => path.endsWith('.md') && body.toLowerCase().includes(q)).slice(0, 10)
          .map(([path, body]) => ({ path, title: parse(path).title, score: 1, snippet: body.slice(0, 240), ...(fallback ? { fallback: true } : {}) })))
      }
    }
    if (req.method === 'GET' && p === '/api/node-types') return send(200, CATALOG)
    if (req.method === 'GET' && p === '/api/environments') return send(200, [...envs.values()].map(e => ({ id: e.id, name: e.name })))
    if ((m = p.match(/^\/api\/environments\/([^/]+)$/))) {
      const id = decodeURIComponent(m[1])
      if (req.method === 'GET') return envs.has(id) ? send(200, envs.get(id)) : send(404, { detail: 'environment not found' })
      if (req.method === 'PUT') {
        const body = await readBody()
        if (!body || !Array.isArray(body.nodes) || !Array.isArray(body.edges)) return send(422, { detail: 'invalid environment' })
        const bad = body.nodes.map(n => n.type).filter(t => !CATALOG.some(c => c.type === t))
        if (bad.length) return send(400, { detail: `unknown node types: ${bad}` })
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
    if (req.method === 'GET' && p === '/api/costs') {
      const envId = url.searchParams.get('env_id')
      const days = Math.max(1, Number(url.searchParams.get('days') ?? 30))
      const cutoff = Date.now() - days * 24 * 60 * 60 * 1000
      const usage = [...runs.values()].filter(r => (!envId || r.env_id === envId) && Date.parse(r.started_at) >= cutoff)
        .flatMap(r => Object.entries(r.usage ?? {}).map(([nodeId, value]) => ({ runId: r.run_id, nodeId, ...value })))
      const summarize = key => {
        const groups = new Map()
        for (const item of usage) {
          const name = item[key] || 'unknown'
          const row = groups.get(name) ?? { [key]: name, _runs: new Set(), runs: 0, steps: 0, tokens_in: 0,
            tokens_out: 0, cost_usd: 0 }
          row._runs.add(item.runId)
          row.steps += 1
          row.tokens_in += Number(item.tokens_in ?? 0)
          row.tokens_out += Number(item.tokens_out ?? 0)
          row.cost_usd += Number(item.cost_usd ?? 0)
          groups.set(name, row)
        }
        return [...groups.values()].sort((a, b) => a[key].localeCompare(b[key])).map(row => {
          row.runs = row._runs.size
          delete row._runs
          return row
        })
      }
      return send(200, { total_usd: usage.reduce((sum, item) => sum + Number(item.cost_usd ?? 0), 0),
        by_route: summarize('route'), by_model: summarize('model'),
        local_share: usage.length ? usage.filter(item => (item.route ?? '').startsWith('local/')).length / usage.length : 0,
        paid_cap_usd: Number(process.env.GLACIER_PAID_CAP_USD ?? 0) })
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

function startRun(env, depth = 0) {
  const run_id = `run-${crypto.randomBytes(4).toString('hex')}`
  const r = {
    run_id, env_id: env.id, status: 'running', started_at: new Date().toISOString(),
    node_states: Object.fromEntries(env.nodes.map(n => [n.id, 'pending'])), outputs: {}, waiting_on: null, resolve: null,
  }
  runs.set(run_id, r)
  execute(structuredClone(env), r, depth).catch(e => { r.status = 'failed'; console.error(e) })
  return run_id
}

function fill(tpl, vars) { return String(tpl ?? '').replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : `{${k}}`)) }

async function execute(env, r, depth = 0) {
  await sleep(150)
  const byId = new Map(env.nodes.map(n => [n.id, n]))
  const out = id => env.edges.filter(e => e.source === id)
  const targeted = new Set(env.edges.map(e => e.target))
  const starts = env.nodes.filter(n => n.type === 'schedule')
  const queue = (starts.length ? starts : env.nodes.filter(n => !targeted.has(n.id))).map(n => ({ id: n.id, prev: null }))
  let execs = 0
  const limit = Number(env.max_steps) || MAX_EXEC
  const loopCounts = new Map()
  const handledByCheck = id => out(id).some(e => byId.get(e.target)?.type === 'check')
  let failed = false
  const summary = []
  while (queue.length) {
    if (execs >= limit) { failed = true; break }
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
        if (code && !handledByCheck(id)) { failed = true; queue.length = 0; next = [] }
        break
      }
      case 'codex': {
        // mock Codex worker: echoes the filled prompt; exit 1 when the prompt contains FAIL
        const prompt = fill(c.prompt || '', { env: env.id, run: r.run_id, prev_output: String(prev?.output ?? '').slice(-8000) })
        const code = /FAIL/.test(prompt) ? 1 : 0
        const text = `codex exit ${code}\ncodex: ${prompt}\n`
        result = { exit_code: code, output: text }
        summary.push(`${id} codex exit ${code}`)
        setState(r, id, code ? 'failed' : 'done', text)
        if (code && !handledByCheck(id)) { failed = true; queue.length = 0; next = [] }
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
      case 'decide': {
        // mock decision: the first option mentioned in the previous step's output, else the first option
        const opts = [...new Set(String(c.options ?? '').split(/[,\n]/).map(s => s.trim()).filter(Boolean))]
        if (opts.length < 2) { setState(r, id, 'failed', 'error: a decision needs at least 2 options'); failed = true; queue.length = 0; next = []; break }
        const ctx = String(prev?.output ?? '').toLowerCase()
        const pick = opts.find(o => ctx.includes(o.toLowerCase())) ?? opts[0]
        setState(r, id, 'done', `decided: ${pick} (by mock)`)
        next = out(id).filter(e => (e.label ?? '').trim().toLowerCase() === pick.toLowerCase())
        result = prev ?? result
        break
      }
      case 'loop': {
        const times = Math.max(0, Math.min(Number(c.times) || 1, MAX_LOOP))
        const k = (loopCounts.get(id) ?? 0) + 1
        loopCounts.set(id, k)
        const again = k <= times
        if (!again) loopCounts.set(id, 0)
        setState(r, id, again ? 'running' : 'done', again ? `iteration ${k} of ${times}` : `finished ${times} of ${times}`)
        next = out(id).filter(e => e.label === (again ? 'again' : 'done'))
        result = prev ?? result
        break
      }
      case 'flow': {
        const child = envs.get(c.env)
        if (depth >= MAX_DEPTH || !child) {
          setState(r, id, 'failed', depth >= MAX_DEPTH ? `error: sub-flows nested more than ${MAX_DEPTH} deep; stopping` : `error: sub-flow '${c.env}' not found`)
          failed = true; queue.length = 0; next = []
          break
        }
        const childId = startRun(child, depth + 1)
        setState(r, id, 'running', `sub-run ${childId} of ${child.id}`)
        while (['running', 'waiting'].includes(runs.get(childId).status)) await sleep(50)
        const st = runs.get(childId).status
        const code = st === 'done' ? 0 : 1
        result = { exit_code: code, output: `sub-run ${childId} of ${child.id}: ${st}` }
        setState(r, id, code ? 'failed' : 'done', result.output)
        if (code && !handledByCheck(id)) { failed = true; queue.length = 0; next = [] }
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
