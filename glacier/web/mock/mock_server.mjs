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
const mockClaims = new Map([['c0ffee01', {
  meta: { id: 'c0ffee01', kind: 'research', summary: 'Best eBay product opportunities', status: 'proposed', updated: new Date().toISOString(), run_id: '' },
  body: '## Problem\nBest eBay product opportunities\n\n## Evidence\n- completed successfully\n- 5 product ideas generated\n- sources included\n\n## Research\n- analyzed 12 categories\n- found 5 high-demand products\n- checked competition and pricing\n\n## Resolution\n',
  summaryRow() { return { id: this.meta.id, kind: this.meta.kind, summary: this.meta.summary, status: this.meta.status, assigned_to: null, updated: this.meta.updated } },
}]])
const mockSecrets = new Set(['SMTP_PASSWORD'])
const mockHygiene = [
  { id: 'h1', kind: 'merge', paths: ['ideas/products.md', 'ideas/products-2.md'], reason: 'These two notes say almost the same thing.', status: 'pending' },
  { id: 'h2', kind: 'archive', paths: ['old/chat-log.md'], reason: 'Not opened or linked for over 90 days.', status: 'pending' },
]
const mockTemplates = [
  { id: 'tpl-daily-report', name: 'Daily report', description: 'Get a daily overview of what matters', author: 'Glacier', license: 'Apache-2.0', review_status: 'reviewed', installable: true,
    template: { id: 'tpl-daily-report', name: 'Daily report', nodes: [{ id: 'n1', type: 'command', config: { command: 'date' }, position: { x: 0, y: 0 } }], edges: [] } },
  { id: 'tpl-folder-backup', name: 'Folder backup', description: 'Copy a folder somewhere safe every night', author: 'Glacier', license: 'Apache-2.0', review_status: 'reviewed', installable: true,
    template: { id: 'tpl-folder-backup', name: 'Folder backup', nodes: [{ id: 'n1', type: 'command', config: { command: 'echo backup' }, position: { x: 0, y: 0 } }], edges: [] } },
]
const runs = new Map() // run_id -> run record
const vault = new Map() // path -> body
const memoryMeta = new Map()
const memoryHistory = new Map()
const assistantProposals = new Map()
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
        const outs = links(body)
        return send(200, { path, body, meta: parse(path), links_out: outs,
          links_out_status: outs.map(t => { const ok = vault.has(`${t}.md`); return { target: t, status: ok ? 'resolved' : 'unresolved', display: ok ? t : `${t} (not written yet)` } }),
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
    if (req.method === 'GET' && p === '/api/home') {
      const now = Date.now()
      const at = minutes => new Date(now - minutes * 60_000).toISOString()
      return send(200, {
        local_ai: { online: true, model: 'qwen3:0.6b' },
        counts: { running: 2, need_you: 4 },
        needs_you: [
          { kind: 'approval', title: 'approval waiting', detail: 'Weekly report', at: at(2), ref: { run_id: 'run-report', node_id: 'approve', env_id: 'weekly-report' } },
          { kind: 'approval', title: 'approval waiting', detail: 'Inbox triage', at: at(9), ref: { run_id: 'run-inbox', node_id: 'confirm', env_id: 'inbox-triage' } },
          { kind: 'claim', title: 'capability_gap', detail: 'Need a calendar connection for this workflow.', at: at(18), ref: { claim_id: '2026-10-07-calendar-claim-a1b2c3' } },
          { kind: 'failed_run', title: 'run failed', detail: 'Nightly checks', at: at(46), ref: { run_id: 'run-tests', env_id: 'nightly-tests' } },
        ],
        running: [
          { run_id: 'run-backup', env_id: 'daily-backup', name: 'Daily backup', status: 'running', step: 2, steps: 4, started_at: at(3) },
          { run_id: 'run-research', env_id: 'market-research', name: 'Market research', status: 'queued', step: 0, steps: 5, started_at: at(1) },
        ],
        recent_notes: [
          { path: 'projects/market-research.md', summary: 'Competitor pricing changed this week.', at: at(32) },
          { path: 'runs/daily-backup.md', summary: 'The latest backup completed successfully.', at: at(115) },
        ],
      })
    }
    if (req.method === 'GET' && p === '/api/node-types') return send(200, CATALOG)
    if (req.method === 'POST' && p === '/api/assistant/chat') {
      const body = await readBody()
      if (!body?.message) return send(400, { detail: 'message is required' })
      const conversationId = body.conversation_id ?? crypto.randomUUID()
      const runId = crypto.randomUUID()
      const messageId = crypto.randomUUID()
      res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' })
      const emit = (type, data = {}) => res.write(`data: ${JSON.stringify({ type, ...data })}\n\n`)
      emit('RUN_STARTED', { threadId: conversationId, runId })
      const automation = /make me|automate|every day|daily/i.test(body.message)
      let reply = `I can help with: ${body.message}`
      if (automation) {
        const id = crypto.randomUUID()
        const flowId = body.message.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'new-flow'
        const flow = { id: flowId, name: 'Daily backup', goal: body.message, created_by: 'assistant',
          nodes: [{ id: 'backup', type: 'command', config: { cmd: 'tar -czf backup.tgz data' }, position: { x: 60, y: 60 } }],
          edges: [], acceptance: [{ kind: 'human', question: 'Did the backup finish?' }] }
        const proposal = { id, conversation_id: conversationId, flow, explanation: 'Creates a daily backup flow.', problems: [] }
        assistantProposals.set(id, proposal)
        const toolCallId = crypto.randomUUID()
        emit('TEXT_MESSAGE_START', { messageId, role: 'assistant' })
        emit('TOOL_CALL_START', { toolCallId, toolCallName: 'propose_flow', parentMessageId: messageId })
        emit('TOOL_CALL_ARGS', { toolCallId, delta: JSON.stringify(proposal) })
        emit('TOOL_CALL_END', { toolCallId })
        reply = proposal.explanation
      }
      if (!automation) emit('TEXT_MESSAGE_START', { messageId, role: 'assistant' })
      if (reply) emit('TEXT_MESSAGE_CONTENT', { messageId, delta: reply })
      emit('TEXT_MESSAGE_END', { messageId })
      const conversationPath = `conversations/${conversationId.replace(/[^a-zA-Z0-9_-]+/g, '-')}.md`
      vault.set(conversationPath, `${vault.get(conversationPath) ?? `# Conversation ${conversationId}\n`}\n\n**You:** ${body.message}\n\n**Assistant:** ${reply}\n`)
      emit('RUN_FINISHED', { threadId: conversationId, runId })
      return res.end()
    }
    if ((m = p.match(/^\/api\/assistant\/proposals\/([^/]+)\/apply$/)) && req.method === 'POST') {
      const proposal = assistantProposals.get(decodeURIComponent(m[1]))
      if (!proposal) return send(404, { detail: 'proposal not found' })
      const body = await readBody()
      if (body?.approve !== true) {
        assistantProposals.delete(proposal.id)
        return send(200, { discarded: true })
      }
      const flow = proposal.flow
      if (envs.has(flow.id)) return send(409, { detail: 'A flow with this name already exists' })
      const bad = flow.nodes.map(node => node.type).filter(type => !CATALOG.some(item => item.type === type))
      if (bad.length) return send(400, { detail: `unknown node types: ${bad}` })
      if (flow.goal && !flow.acceptance?.length) return send(400, { detail: 'This goal has no check yet. Add a way to check it is done before running it.' })
      envs.set(flow.id, flow)
      const commit = commitId()
      vault.set(`environments/${flow.id}.json`, JSON.stringify(flow, null, 2))
      assistantProposals.delete(proposal.id)
      return send(200, { saved: true, commit })
    }
    // ---- settings (screen development only) ----
    if (p === '/api/secrets' && req.method === 'GET') return send(200, [...mockSecrets].sort())
    if ((m = p.match(/^\/api\/secrets\/([A-Za-z0-9_.-]+)$/))) {
      if (req.method === 'PUT') { const b = await readBody(); if (!b?.value) return send(422, { detail: 'value required' }); mockSecrets.add(m[1]); return send(200, { saved: true }) }
      if (req.method === 'DELETE') { mockSecrets.delete(m[1]); return send(200, { deleted: true }) }
    }
    if (p === '/api/costs') return send(200, { total_usd: 0, paid_cap_usd: 0, local_share: 0.8, by_route: [], by_model: [{ model: 'qwen3:0.6b', runs: 12, steps: 40, tokens_in: 52000, tokens_out: 9000, cost_usd: 0 }] })
    if (p === '/api/memory/compat') return send(200, { ok: true, notes_checked: vault.size, problems: [] })
    if (p === '/api/system/settings') return send(200, { mode: 'standard', local_model: 'qwen3:0.6b', max_parallel_runs: 2 })
    if (p === '/api/system/check') return send(200, { cpu_cores: 8, memory_gb: 16, disk_free_gb: 100, ollama_models: ['qwen3:0.6b'], tools: { ollama: { found: true, version: '0.12' }, git: { found: true, version: '2.43' } }, recommended: { mode: 'standard', local_model: 'qwen3:0.6b', max_parallel_runs: 2 }, messages: [] })
    // ---- memory cleanup + file drop + chat import (screen development only) ----
    if (p === '/api/memory/hygiene' && req.method === 'GET') return send(200, mockHygiene.filter(h => h.status === 'pending').map(({ status, ...h }) => h))
    if (p === '/api/memory/hygiene/scan' && req.method === 'POST') return send(200, mockHygiene.filter(h => h.status === 'pending').map(({ status, ...h }) => h))
    if ((m = p.match(/^\/api\/memory\/hygiene\/([^/]+)$/)) && req.method === 'POST') {
      const h = mockHygiene.find(x => x.id === m[1]); if (!h) return send(404, { detail: 'proposal not found' })
      const body = await readBody(); h.status = body.approve ? 'approved' : 'rejected'
      return send(200, { id: h.id, status: h.status, ...(body.approve ? { commit: commitId() } : {}) })
    }
    if (p === '/api/imports' && req.method === 'GET') return send(200, [{ source: 'chatgpt', last_import: new Date(Date.now() - 864e5).toISOString(), added: 42, updated: 3, unchanged: 100 }])
    if (p === '/api/sessions' && req.method === 'GET') return send(200, [
      { id: 'opencode:ses_demo', tool: 'opencode', source: 'opencode', started: new Date(Date.now() - 72e5).toISOString(), updated: new Date(Date.now() - 6e5).toISOString(), title: 'Fix the login page', cwd: '/home/me/site', active: false },
      { id: 'codex-demo', tool: 'codex', started: new Date(Date.now() - 864e5).toISOString(), updated: new Date(Date.now() - 36e5).toISOString(), title: 'Add tests for the parser', cwd: '/home/me/parser', active: true }])
    if ((m = p.match(/^\/api\/sessions\/([^/]+)$/)) && req.method === 'GET') return send(200, { id: decodeURIComponent(m[1]), tool: 'opencode', source: 'opencode', started: new Date(Date.now() - 72e5).toISOString(), updated: new Date().toISOString(), title: 'Fix the login page', cwd: '/home/me/site', active: false,
      events: [{ type: 'user_message', text: 'The login button does nothing' }, { type: 'command', text: 'Ran command: npm test' }, { type: 'assistant_message', text: 'Fixed the click handler and added a test.' }] })
    if ((m = p.match(/^\/api\/sessions\/([^/]+)\/save-to-memory$/)) && req.method === 'POST') return send(200, { saved: true, path: 'sessions/opencode_ses_demo-abc.md' })
    if (p === '/api/imports/refresh' && req.method === 'POST') return send(200, { chatgpt: { added: 2, updated: 1, unchanged: 145 } })
    if ((p === '/api/files' || p === '/api/imports') && req.method === 'POST') {
      let size = 0; await new Promise(r => { req.on('data', c => (size += c.length)); req.on('end', r) })
      return send(200, p === '/api/files' ? { name: 'upload', size, duplicate: false } : { conversations: 3, notes: 3 })
    }
    // ---- claims + templates (screen development only) ----
    if (p === '/api/claims' && req.method === 'GET') {
      const st = url.searchParams.get('status')
      return send(200, [...mockClaims.values()].map(c => c.summaryRow()).filter(c => !st || c.status === st))
    }
    if ((m = p.match(/^\/api\/claims\/([^/]+)$/)) && req.method === 'GET') {
      const c = mockClaims.get(m[1]); return c ? send(200, { meta: c.meta, body: c.body }) : send(404, { detail: 'claim not found' })
    }
    if ((m = p.match(/^\/api\/claims\/([^/]+)\/decision$/)) && req.method === 'POST') {
      const c = mockClaims.get(m[1]); if (!c) return send(404, { detail: 'claim not found' })
      const body = await readBody()
      const status = { approve: 'resolved', reject: 'closed', research_more: 'researching' }[body.action]
      if (!status) return send(400, { detail: 'action must be approve, reject or research_more' })
      c.meta.status = status; c.body += `\n- Owner decision: ${body.action}`
      return send(200, { status })
    }
    if (p === '/api/templates' && req.method === 'GET') return send(200, mockTemplates)
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
    if (req.method === 'GET' && (m = p.match(/^\/api\/runs\/([^/]+)\/explain$/))) {
      const r = runs.get(decodeURIComponent(m[1]))
      if (!r) return send(404, { detail: 'run not found' })
      const labels = new Map(CATALOG.map(item => [item.type, item.label]))
      const steps = r.graph.nodes.map((node, index) => {
        const state = r.node_states[node.id] ?? 'pending'
        const label = labels.get(node.type) ?? 'Step'
        const output = String(r.outputs[node.id] ?? '').replace(/\s+/g, ' ').trim().slice(0, 120)
        const sentence = state === 'failed'
          ? `Step ${index + 1} (${label}) failed: ${/missing (?:secret|password)|password is missing/i.test(output) ? 'Add the missing password in Settings > Secrets, then run again.' : /command not found/i.test(output) ? 'Install the missing program, then run again.' : /timed out|timeout/i.test(output) ? 'The step took too long. Check its time limit or try again.' : /check failed|check .*-> no/i.test(output) ? 'The check did not pass. Review its result and fix the earlier step.' : 'It stopped with an error. Open the step\'s output for details.'}`
          : state === 'waiting' ? `Step ${index + 1} (${label}) is waiting for your approval.`
            : state === 'done' ? `Step ${index + 1} (${label}) finished.${output ? ` ${output}` : ''}`
              : state === 'skipped' ? `Step ${index + 1} (${label}) was skipped.`
                : state === 'running' ? `Step ${index + 1} (${label}) is running.`
                  : `Step ${index + 1} (${label}) has not started.`
        return { node_id: node.id, label, state, sentence }
      })
      const acceptance = r.graph.acceptance ?? []
      const verified = acceptance.length && ['done', 'failed', 'rejected'].includes(r.status)
        ? r.status === 'done' && acceptance.every((_, index) => r.checks?.[index] === true)
        : null
      const waitingNode = r.graph.nodes.find(node => node.id === r.waiting_on)
      const prompt = waitingNode?.config?.prompt ?? ''
      const needs_you = r.status === 'waiting' ? `Decide whether to approve${prompt ? `: ${prompt}` : ' this step.'}` : null
      const name = r.graph.name ?? 'This run'
      const failed = steps.find(step => step.state === 'failed')
      const summary = r.status === 'waiting' ? `${name} is waiting for your decision.`
        : r.status === 'rejected' ? `${name} stopped because an approval was rejected.`
          : r.status === 'failed' ? (failed ? `${failed.sentence}` : `${name} stopped before it finished. Open the step's output for details.`)
            : `${name} finished ${steps.filter(step => step.state === 'done').length} steps.${verified === true ? ' Every check passed.' : acceptance.length ? ' The run finished, but not every check passed.' : ''}`
      return send(200, { summary, steps, verified, needs_you })
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
    graph: structuredClone(env), checks: {}, usage: {}, node_states: Object.fromEntries(env.nodes.map(n => [n.id, 'pending'])), outputs: {}, waiting_on: null, resolve: null,
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
        r.checks[env.acceptance ? Math.max(0, env.acceptance.findIndex(check => check.kind === 'command')) : 0] = ok
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
