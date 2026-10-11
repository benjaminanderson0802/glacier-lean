// In-memory mock of the Glacier core v0 backend contract (docs/CONTRACT.md), for UI work and e2e tests.
// Usage: node mock/mock_server.mjs [port]   (default: an ephemeral free port, or env MOCK_PORT)
// Commands are NOT executed: a command's output is "$ <cmd>" plus a fake line; its exit code is 1 when the
// command text contains "fail" or "exit 1", else 0. A codex node's output is "codex: <prompt>". Each node step takes STEP_MS (default 250ms).
import http from 'node:http'
import crypto from 'node:crypto'
import { WebSocketServer } from 'ws'
import { readFileSync } from 'node:fs'

// same node-type catalog the real backend serves
const CATALOG = JSON.parse(readFileSync(new URL('../../contract/node_types.json', import.meta.url), 'utf8')).types
const HTTP_NODE = {
  type: 'http_request', label: 'Call a web API',
  description: 'Send a request to an approved API and pass its response to the next step.',
  fields: [
    { key: 'method', label: 'Method', default: 'GET', options: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'] },
    { key: 'url', label: 'Web address', placeholder: 'https://api.example.org/items', default: '' },
    { key: 'allowed_sites', label: 'Allowed sites', placeholder: 'api.example.org', default: '' },
    { key: 'headers', label: 'Headers', placeholder: 'Authorization: Bearer {secret:API_TOKEN}', default: '', optional: true, multiline: true },
    { key: 'body', label: 'Request body', placeholder: 'Text or JSON; {prev_output}, {run}, {env} are available', default: '', optional: true, multiline: true },
    { key: 'body_type', label: 'Body format', default: 'Text', options: ['Text', 'JSON'], optional: true },
    { key: 'timeout', label: 'Timeout in seconds', default: '20', optional: true },
    { key: 'expect_status', label: 'Expected status', default: '2xx', placeholder: '2xx or an exact status such as 201', optional: true },
    { key: 'allow_private_network', label: 'This API runs on this computer or my network', default: 'No', options: ['No', 'Yes'], optional: true },
  ], branches: null, worker: true, changing_methods: ['POST', 'PUT', 'PATCH', 'DELETE'],
}
const BUSINESS_NODES = [
  { type: 'json_transform', label: 'Change JSON', description: 'Set fields, filter, merge, split, or remove duplicate items.', fields: [
    { key: 'operation', label: 'Operation', default: 'set_fields', options: ['set_fields', 'filter', 'merge', 'split', 'dedupe'] },
    { key: 'fields', label: 'Fields to set (JSON)', placeholder: '{"status":"ready"}', default: '{}', multiline: true },
    { key: 'field', label: 'Field to check', placeholder: 'status', default: '', optional: true },
    { key: 'equals', label: 'Matches', placeholder: 'ready', default: '', optional: true },
    { key: 'data', label: 'Extra data (JSON)', placeholder: '{}', default: '{}', optional: true, multiline: true },
    { key: 'key', label: 'Unique field', placeholder: 'id', default: '', optional: true },
    { key: 'retries', label: 'Retries if it fails', placeholder: '0', default: '0', optional: true },
  ], branches: null },
  { type: 'data_table', label: 'Local table', description: 'Save, update, find, and deduplicate rows on this computer.', fields: [
    { key: 'table', label: 'Table name', placeholder: 'customers', default: 'customers' },
    { key: 'operation', label: 'Operation', default: 'upsert', options: ['insert', 'upsert', 'query', 'dedupe'] },
    { key: 'key', label: 'Unique field', placeholder: 'email', default: 'id', optional: true },
    { key: 'record', label: 'Row (JSON)', placeholder: '{"id":1,"name":"Ada"}', default: '{}', optional: true, multiline: true },
    { key: 'match', label: 'Find rows (JSON)', placeholder: '{"status":"new"}', default: '{}', optional: true, multiline: true },
    { key: 'retries', label: 'Retries if it fails', placeholder: '0', default: '0', optional: true },
  ], branches: null },
  { type: 'csv_file', label: 'Read or write CSV', description: "Read or write a CSV file inside this flow's folder.", fields: [
    { key: 'operation', label: 'Operation', default: 'read', options: ['read', 'write'] },
    { key: 'path', label: 'CSV file', placeholder: 'contacts.csv', default: 'contacts.csv' },
    { key: 'data', label: 'Rows to write (JSON)', placeholder: '[{"name":"Ada"}]', default: '[]', optional: true, multiline: true },
    { key: 'retries', label: 'Retries if it fails', placeholder: '0', default: '0', optional: true },
  ], branches: null },
  { type: 'delay', label: 'Wait', description: 'Pause this flow for a chosen time.', fields: [
    { key: 'seconds', label: 'Seconds', placeholder: '30', default: '30' },
    { key: 'retries', label: 'Retries if it fails', placeholder: '0', default: '0', optional: true },
  ], branches: null, worker: true },
  { type: 'structured_ai', label: 'Ask AI for JSON', description: 'Ask an owner-configured model route or the signed-in Codex CLI for checked JSON data.', fields: [
    { key: 'prompt', label: 'What should AI do?', placeholder: 'Classify this item: {prev_output}', default: '', multiline: true },
    { key: 'schema', label: 'Required JSON shape', placeholder: '{"type":"object","properties":{"ok":{"type":"boolean"}},"required":["ok"]}', default: '{"type":"object"}', multiline: true },
    { key: 'engine', label: 'AI engine', default: 'configured', options: ['configured', 'codex'] },
    { key: 'routes', label: 'Model routes', placeholder: 'all available free routes', default: '', optional: true },
    { key: 'timeout', label: 'Time limit (seconds)', placeholder: '600', default: '600', optional: true },
    { key: 'retries', label: 'Retries if it fails', placeholder: '0', default: '0', optional: true },
  ], branches: null, worker: true },
  { type: 'email_send', label: 'Write or send email', description: 'Save a draft on this computer or send through your SMTP account after approval.', fields: [
    { key: 'draft_only', label: 'Keep as a draft', default: 'Yes', options: ['Yes', 'No'] },
    { key: 'host', label: 'SMTP server', placeholder: 'smtp.gmail.com', default: '', optional: true },
    { key: 'port', label: 'SMTP port', default: '587', optional: true },
    { key: 'user', label: 'Email account', placeholder: 'you@example.com', default: '', optional: true },
    { key: 'password', label: 'App password from Settings > Secrets', placeholder: '{secret:EMAIL_APP_PASSWORD}', default: '', optional: true },
    { key: 'from', label: 'From', placeholder: 'you@example.com', default: '' },
    { key: 'to', label: 'To', placeholder: 'person@example.com', default: '' },
    { key: 'subject', label: 'Subject', placeholder: 'Hello {env}', default: '' },
    { key: 'body', label: 'Message', placeholder: 'Write your message here', default: '', multiline: true },
    { key: 'timeout', label: 'Time limit in seconds', default: '30', optional: true },
  ], branches: null, worker: true },
  { type: 'email_read', label: 'Search email', description: 'Find and read recent messages from your IMAP mailbox without marking them as read.', fields: [
    { key: 'host', label: 'IMAP server', placeholder: 'imap.gmail.com', default: '' },
    { key: 'port', label: 'IMAP port', default: '993', optional: true },
    { key: 'user', label: 'Email account', placeholder: 'you@example.com', default: '' },
    { key: 'password', label: 'App password from Settings > Secrets', placeholder: '{secret:EMAIL_APP_PASSWORD}', default: '' },
    { key: 'folder', label: 'Mailbox', placeholder: 'INBOX', default: 'INBOX', optional: true },
    { key: 'search', label: 'Search', placeholder: 'UNSEEN or FROM name@example.com', default: 'UNSEEN' },
    { key: 'limit', label: 'Maximum messages', default: '10', optional: true },
    { key: 'timeout', label: 'Time limit in seconds', default: '30', optional: true },
    { key: 'retries', label: 'Retries if it fails', default: '0', optional: true },
  ], branches: null, worker: true },
  { type: 'email_trigger', label: 'When an email arrives', description: 'Poll an IMAP mailbox over TLS and start once for each new matching message.', fields: [
    { key: 'host', label: 'IMAP server', placeholder: 'imap.gmail.com', default: '' },
    { key: 'port', label: 'IMAP port', default: '993', optional: true },
    { key: 'user', label: 'Email account', placeholder: 'you@example.com', default: '' },
    { key: 'password', label: 'App password from Settings > Secrets', placeholder: '{secret:EMAIL_APP_PASSWORD}', default: '' },
    { key: 'folder', label: 'Mailbox', placeholder: 'INBOX', default: 'INBOX', optional: true },
    { key: 'search', label: 'Only match', placeholder: 'UNSEEN or FROM name@example.com', default: 'UNSEEN' },
    { key: 'limit', label: 'Maximum messages per check', default: '10', optional: true },
  ], branches: null, worker: true },
]
const NODE_CATALOG = [...CATALOG, ...BUSINESS_NODES]

const PORT = Number(process.argv[2] ?? process.env.MOCK_PORT ?? 0)
const STEP_MS = Number(process.env.STEP_MS ?? 250)
const MAX_EXEC = 500
const MAX_DEPTH = 5
const MAX_LOOP = 1000

const envs = new Map() // id -> Environment
const mockClaims = new Map([['c0ffee01', {
  meta: { id: 'c0ffee01', kind: 'research', summary: 'Best eBay product opportunities', status: 'proposed', updated: new Date().toISOString(), run_id: '' },
  body: '## Problem\nBest eBay product opportunities\n\n## Evidence\n- completed successfully\n- 5 product ideas generated\n- sources included\n\n## Research\n- analyzed 12 categories\n- found 5 high-demand products\n- checked competition and pricing\n\n## Resolution\n',
  summaryRow() { return { id: this.meta.id, kind: this.meta.kind, summary: this.meta.summary, status: this.meta.status, assigned_to: null, updated: this.meta.updated } },
}], ['c0ffee02', {
  meta: { id: 'c0ffee02', kind: 'bug', summary: 'Step fetch in flow nightly-sync keeps failing the same way', status: 'proposed', updated: new Date().toISOString(), run_id: 'run-nightly' },
  body: '## Problem\nStep fetch keeps failing\n\n## Evidence\n- failed 3 times with the same error\n\n## Research\n- the site changed its address\n\n## Resolution\n',
  summaryRow() { return { id: this.meta.id, kind: this.meta.kind, summary: this.meta.summary, status: this.meta.status, assigned_to: null, updated: this.meta.updated } },
}]])
const mockSecrets = new Set(['SMTP_PASSWORD'])
let mockApprovalDone = false
const mockVentures = new Map([['truck-dispatch', {
  slug: 'truck-dispatch', name: 'Truck dispatch', status: 'setting_up',
  flows: [{ env_id: 'dispatch', dry_run_env_id: 'dispatch-preview' }], schedule: { cron: '0 8 * * *' },
  next_run: new Date(Date.now() + 3600_000).toISOString(), today: { runs: 4, completed: 3, failed: 0 },
  your_steps: [{ id: 'fleet-key', title: 'connect the fleet account', instructions: 'Paste both keys into the fields on this step. Glacier saves them in this computer’s keychain.', link: 'https://fleet.example.test/settings/api', secrets: [{ name: 'FLEET_KEY', label: 'Fleet API key' }, { name: 'FLEET_REGION', label: 'Fleet region key' }], done: false }],
} ]])
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
const fixedMockRuns = new Map()
const hiddenRuns = new Set()
const deletedFlows = new Map()
const vault = new Map() // path -> body
const memoryMeta = new Map()
const memoryHistory = new Map()
const deletedNotes = new Map()
const renames = new Map()
const assistantProposals = new Map()
const mockTeams = new Map()
const deletedItems = new Map()
const conversations = new Map()  // id -> { title, messages: [{ who, text, at }] }
const messageSessionRows = [
  { id: 'codex:mock-codex-session', source: 'codex', title: 'Review the parser', last_text: 'The parser handles empty input.', last_at: '2026-10-08T12:00:00.000Z', unread: false, can_send: true },
  { id: 'claude-code:mock-claude-session', source: 'claude', title: 'Plan a refactor', last_text: 'I found two small changes.', last_at: '2026-10-08T11:00:00.000Z', unread: false, can_send: true },
  { id: 'codex:mock-codex-unavailable', source: 'codex', title: 'Unavailable Codex session', last_text: 'Earlier work.', last_at: '2026-10-08T10:30:00.000Z', unread: false, can_send: false, can_send_reason: 'Codex CLI is not installed' },
  { id: 'opencode:mock-opencode-session', source: 'opencode', title: 'Local model notes', last_text: 'Read-only mirrored session.', last_at: '2026-10-08T10:00:00.000Z', unread: false, can_send: false },
  { id: 'gemini:mock-gemini-session', source: 'gemini', title: 'Research notes', last_text: 'Read-only mirrored session.', last_at: '2026-10-08T09:00:00.000Z', unread: false, can_send: false },
]
const messageHistory = new Map()
const deletedConversations = new Map()
const deletedClaims = new Map()
const uploadedFiles = new Map()
const deletedFiles = new Map()
const deletedTemplates = new Map()
const sleep = ms => new Promise(r => setTimeout(r, ms))
let starterApplied = false
const commitId = () => crypto.randomBytes(20).toString('hex').slice(0, 7)

let mockSeenVersion = '0.2.0'
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
    if (p === '/api/ventures' && req.method === 'GET') return send(200, [...mockVentures.values()])
    if ((m = p.match(/^\/api\/ventures\/([a-z0-9-]+)\/(pause|resume)$/)) && req.method === 'POST') {
      const venture = mockVentures.get(m[1]); if (!venture) return send(404, { detail: 'venture not found' })
      venture.status = m[2] === 'pause' ? 'paused' : 'running'
      return send(200, { paused: m[2] === 'pause', flows: venture.flows.map(flow => flow.env_id) })
    }
    if ((m = p.match(/^\/api\/ventures\/([a-z0-9-]+)\/run$/)) && req.method === 'POST') {
      const venture = mockVentures.get(m[1]); if (!venture) return send(404, { detail: 'venture not found' })
      const body = await readBody()
      if (body?.dry_run === false) return send(400, { detail: 'Venture runs from this screen must use the dry-run flow' })
      const flow = venture.flows.find(item => item.dry_run_env_id) ?? venture.flows[0]
      const env_id = flow.dry_run_env_id
      if (!env_id) return send(409, { detail: 'dry-run flow not configured' })
      const graph = envs.get(env_id) ?? { id: env_id, name: `${venture.name} dry run`, nodes: [
        { id: 'preview', type: 'command', config: { cmd: 'echo preview only' }, position: { x: 80, y: 80 } },
      ], edges: [] }
      envs.set(env_id, graph)
      venture.today.runs += 1
      const run_id = startRun(graph)
      return send(200, { run_id, env_id, dry_run: true })
    }
    if ((m = p.match(/^\/api\/ventures\/([a-z0-9-]+)\/steps\/([A-Za-z0-9_.-]+)\/done$/)) && req.method === 'POST') {
      const venture = mockVentures.get(m[1]), step = venture?.your_steps.find(item => item.id === m[2])
      if (!step) return send(404, { detail: 'step not found' })
      const body = await readBody()
      if (step.secrets?.length) {
        if (!step.secrets.every(field => body?.values?.[field.name]?.trim())) return send(400, { detail: 'enter each key first' })
        step.secrets.forEach(field => mockSecrets.add(field.name))
      } else if (step.secret_name) { if (!body?.value) return send(400, { detail: 'paste the key first' }); mockSecrets.add(step.secret_name) }
      step.done = true
      return send(200, { done: true, secret_name: step.secret_name, secret_names: (step.secrets ?? []).map(field => field.name) })
    }
    if (p === '/api/teams' && req.method === 'GET') return send(200, [...mockTeams.values()].map(team => ({ team_id: team.team_id, name: team.plan.vision.goal, status: team.status, done: Object.values(team.tasks).filter(t => t.status === 'done').length, tasks: Object.keys(team.tasks).length, passing: Object.values(team.features).filter(f => f.status === 'passing').length, feature_count: team.plan.features.length, needs_owner: Object.values(team.tasks).filter(t => t.status === 'awaiting_approval').length })))
    if (p === '/api/build/vision' && req.method === 'POST') { const body = await readBody(); const path = `visions/${crypto.randomUUID()}.md`; vault.set(path, JSON.stringify(body.vision)); return send(200, { confirmed: true, path, vision: body.vision }) }
    if (p === '/api/build/draft-spec' && req.method === 'POST') { const path = `visions/${crypto.randomUUID()}.md`; return send(200, { path, vision: { goal: 'Help freelancers track project deadlines', requirements: ['The system shall list projects and their deadlines', 'When a deadline changes, the system shall save the updated date'], done: ['A freelancer can add a project and see its deadline'], out_of_scope: ['Accounts and subscriptions'] }, spec: { requirements: ['The system shall list projects and their deadlines', 'When a deadline changes, the system shall save the updated date'], acceptance: ['A saved project appears with its deadline after reload'], out_of_scope: ['Accounts and subscriptions'] } }) }
    if (p === '/api/build/spec' && req.method === 'POST') { const body = await readBody(); return send(200, { approved: true, spec: body.spec }) }
    if (p === '/api/build/interview' && req.method === 'POST') { const body = await readBody(); const reply = 'Offline access and no subscriptions are clear. Who will use it day to day?'; const old = conversations.get(body.conversation_id) ?? { title: 'Build interview', messages: [] }; old.messages.push({ who: 'user', text: body.message }, { who: 'assistant', text: reply }); conversations.set(body.conversation_id, old); return send(200, { conversation_id: body.conversation_id, reply, readiness: 85, conversation_path: `conversations/${body.conversation_id}.md` }) }
    if (p === '/api/build/plan' && req.method === 'POST') { const plan = { vision: { goal: 'Personal project hub', done: ['A working project hub'] }, spec: { requirements: ['The hub shall list projects'], out_of_scope: ['Team accounts'], acceptance: ['The project list opens'] }, features: [{ id: 'list', title: 'Project list', acceptance: ['List appears'] }], harness: { startup_script: 'npm start', smoke_test: 'npm test', checks: ['npm test'] }, team: { worker_mode: 'parallel', parallel_limit: 2, roles: [{ id: 'lead', charter: 'Coordinate handoffs' }, { id: 'builder', charter: 'Build the feature' }, { id: 'evaluator', charter: 'Check the feature independently' }] }, tasks: [{ id: 'build-list', title: 'Build project list', role: 'builder', feature_id: 'list', acceptance: ['List appears'], requires_approval: true }, { id: 'check-list', title: 'Evaluate project list', role: 'evaluator', feature_id: 'list', acceptance: ['List appears'] }] }; return send(200, { plan, approved: false }) }
    if (p === '/api/teams' && req.method === 'POST') { const body = await readBody(), team_id = `team-${mockTeams.size + 1}`; const team = { team_id, status: 'approved', plan: body.plan, tasks: Object.fromEntries(body.plan.tasks.map(task => [task.id, { status: 'pending', attempts: 0, replans: 0 }])), features: Object.fromEntries(body.plan.features.map(f => [f.id, { status: 'pending' }])), progress_log: 'Team approved. Waiting for first task.' }; mockTeams.set(team_id, team); return send(200, { team_id, status: team.status, plan: team.plan }) }
    if ((m = p.match(/^\/api\/teams\/([^/]+)$/)) && req.method === 'GET') { const team = mockTeams.get(m[1]); return team ? send(200, team) : send(404, { detail: 'team not found' }) }
    if ((m = p.match(/^\/api\/teams\/([^/]+)\/run$/)) && req.method === 'POST') { const team = mockTeams.get(m[1]); if (!team) return send(404, { detail: 'team not found' }); team.status = 'waiting'; team.tasks['build-list'].status = 'awaiting_approval'; team.tasks['build-list'].attempts = 1; team.progress_log = 'Cycle 1: builder handed off Project list for owner approval.'; return send(200, { team_id: m[1], status: 'running' }) }
    if ((m = p.match(/^\/api\/teams\/([^/]+)\/tasks\/([^/]+)\/approve$/)) && req.method === 'POST') { const team = mockTeams.get(m[1]), body = await readBody(); if (!team) return send(404, { detail: 'team not found' }); team.tasks[m[2]].status = body.approved ? 'done' : 'rejected'; if (body.approved) { team.tasks['check-list'].status = 'done'; team.features.list = { status: 'passing', evaluator_evidence: 'Project list smoke check passed.' }; team.status = 'done'; team.progress_log += '\nEvaluator passed Project list. Vision complete.' } else team.status = 'needs_owner'; return send(200, { team_id: m[1], task_id: m[2], approved: body.approved }) }
    if ((m = p.match(/^\/api\/teams\/([^/]+)\/(pause|resume|stop)$/)) && req.method === 'POST') { const team = mockTeams.get(m[1]); if (!team) return send(404, { detail: 'team not found' }); team.status = { pause: 'paused', resume: 'running', stop: 'stopped' }[m[2]]; return send(200, { team_id: m[1], status: team.status }) }
    if ((m = p.match(/^\/api\/teams\/([^/]+)$/)) && req.method === 'DELETE') { const team = mockTeams.get(m[1]); if (!team) return send(404, { detail: 'team not found' }); const undo_id = crypto.randomUUID(); deletedItems.set(undo_id, ['team', team]); mockTeams.delete(m[1]); return send(200, { deleted: true, undo_id }) }
    if (p === '/api/build/undo-delete' && req.method === 'POST') { const body = await readBody(), item = deletedItems.get(body.undo_id); if (!item) return send(404, { detail: 'undo expired' }); if (item[0] === 'team') mockTeams.set(item[1].team_id, item[1]); deletedItems.delete(body.undo_id); return send(200, { restored: true }) }
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
      if (req.method === 'DELETE' && p === '/api/memory/note') {
        const path = url.searchParams.get('path')
        if (!path || path.includes('..') || !path.endsWith('.md') || path.startsWith('claims/')) return send(400, { detail: 'That note path is not allowed' })
        if (!vault.has(path)) return send(404, { detail: 'Note not found' })
        const commit = commitId(), history = memoryHistory.get(path) ?? []
        deletedNotes.set(commit, { path, body: vault.get(path), meta: memoryMeta.get(path) })
        history.unshift({ commit, author: 'owner', date: new Date().toISOString(), message: `[owner] delete ${path}`, body: null })
        memoryHistory.set(path, history); vault.delete(path); memoryMeta.delete(path)
        broadcast({ type: 'memory', path, change: 'deleted', author: 'owner', run_id: '' })
        return send(200, { deleted: true, path, commit })
      }
      if (req.method === 'POST' && p === '/api/memory/undo-delete') {
        const item = await readBody(), deleted = deletedNotes.get(item?.commit)
        if (!deleted || deleted.path !== item.path) return send(404, { detail: 'Removed note not found' })
        if (vault.has(item.path)) return send(409, { detail: 'A note with that name already exists' })
        vault.set(item.path, deleted.body); if (deleted.meta) memoryMeta.set(item.path, deleted.meta)
        deletedNotes.delete(item.commit)
        broadcast({ type: 'memory', path: item.path, change: 'created', author: 'owner', run_id: '' })
        return send(200, { restored: true, path: item.path, commit: commitId() })
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
      const renameNote = (from, to) => {
        if (!vault.has(from)) return [404, { detail: 'That note could not be found' }]
        if (vault.has(to)) return [409, { detail: 'A note already exists at that path' }]
        vault.set(to, vault.get(from)); vault.delete(from)
        memoryMeta.set(to, memoryMeta.get(from)); memoryMeta.delete(from)
        memoryHistory.set(to, memoryHistory.get(from) ?? []); memoryHistory.delete(from)
        const a = clean(from), b = clean(to)
        for (const [other, text] of vault) if (other !== to) {
          const next = text.replace(/\[\[([^\]|#]+)([^\]]*)\]\]/g, (all, target, rest) => clean(target.trim()) === a ? `[[${b}${rest}]]` : all)
          if (next !== text) vault.set(other, next)
        }
        const commit = commitId(); renames.set(commit, { from, to })
        broadcast({ type: 'memory', path: to, change: 'created', author: 'owner', run_id: '' })
        return [200, { path: to, commit }]
      }
      if (req.method === 'POST' && p === '/api/memory/rename') {
        const item = await readBody()
        if (!item?.from || !item?.to || !String(item.to).endsWith('.md')) return send(400, { detail: 'Provide the old and new note paths' })
        return send(...renameNote(item.from, item.to))
      }
      if (req.method === 'POST' && p === '/api/memory/undo') {
        const item = await readBody()
        const rn = item?.commit && [...renames].find(([c]) => c.startsWith(item.commit))
        if (rn) { const [status, out] = renameNote(rn[1].to, rn[1].from); return send(status, status === 200 ? { path: item.path, commit: out.commit } : { detail: "That rename can't be undone because a note now uses the old name" }) }
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
      const healthDate = new Date(now).toISOString().slice(0, 10)
      const ventureSteps = [
        ...[...mockVentures.values()].flatMap(venture => venture.your_steps.filter(step => !step.done).map(step => ({ kind: 'your_step', title: step.title, detail: step.instructions, instructions: step.instructions, links: [step.link], secret_name: step.secret_name, secrets: step.secrets, at: new Date().toISOString(), ref: { venture_slug: venture.slug, step_id: step.id } }))),
        ...(!mockApprovalDone ? [{ kind: 'your_step', title: 'Your step: review the dispatch list', detail: 'Your step: review the dispatch list', instructions: 'Approve the route before any driver is assigned.', at: at(1), ref: { run_id: 'run-dispatch-waiting', node_id: 'review', env_id: 'dispatch' } }] : []),
      ]
      const healthNotePath = `health/glacier-health-${healthDate}.md`
      if (!vault.has(healthNotePath)) vault.set(healthNotePath, `# Glacier health — ${healthDate}\n\n- Failed runs in the last day: 1\n- Runs timed out after 24 hours: 0\n- Steps waiting on you: 2\n- Data folder size: 5.0 MB\n`)
      return send(200, {
        local_ai: { online: true, model: 'qwen3:0.6b' },
        health: { date: healthDate, failed_runs: 1, stuck_runs: 0, waiting_for_owner: 2, data_bytes: 5242880, note_path: healthNotePath },
        next_runs: [{ env_id: 'daily-backup', name: 'Daily backup', next_run: new Date(now + 3600_000).toISOString() }],
        venture_digest: { date: new Date(now).toISOString().slice(0, 10), ventures: mockVentures.size, runs: [...mockVentures.values()].reduce((sum, venture) => sum + venture.today.runs, 0), completed: [...mockVentures.values()].reduce((sum, venture) => sum + venture.today.completed, 0), failed: [...mockVentures.values()].reduce((sum, venture) => sum + venture.today.failed, 0), waiting_for_you: [...mockVentures.values()].reduce((sum, venture) => sum + venture.your_steps.filter(step => !step.done).length, 0) + (mockApprovalDone ? 0 : 1) },
        venture_steps: ventureSteps,
        counts: { running: 2, need_you: 6 + ventureSteps.length },
        needs_you: [
          { kind: 'approval', title: 'approval waiting', detail: 'Weekly report', at: at(2), ref: { run_id: 'run-report', node_id: 'approve', env_id: 'weekly-report' } },
          { kind: 'approval', title: 'approval waiting', detail: 'Inbox triage', at: at(9), ref: { run_id: 'run-inbox', node_id: 'confirm', env_id: 'inbox-triage' } },
          { kind: 'claim', title: 'capability_gap', detail: 'Need a calendar connection for this workflow.', at: at(18), ref: { claim_id: '2026-10-07-calendar-claim-a1b2c3' } },
          { kind: 'failed_run', title: 'run failed', detail: 'Nightly checks', at: at(46), ref: { run_id: 'run-tests', env_id: 'nightly-tests' } },
          ...ventureSteps,
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
    if (p === '/api/e2e/control-fixtures' && req.method === 'POST') {
      const base = new Date().toISOString()
      const fixtureNotes = [
        ['projects/market-research.md', '# Market research\n\nThe strongest rise came from short clips with a useful first day. Views rose 35% and saves rose 20% in the first week.\n\nNext: [[decisions/strong-rise-rule]] and [[projects/sponsor-shortlist]]. #research #video', 'owner'],
        ['projects/sponsor-shortlist.md', '# Sponsor shortlist\n\nStart with the two partners who asked for family travel and outdoor stories. Send the first sample after the next edit review.\n\nUse the backup plan in [[projects/backup-plan]]. #sponsors #video', 'worker:granite3.3:2b'],
        ['projects/backup-plan.md', '# Backup plan\n\nKeep the original clips on the local drive. Copy finished exports to the external drive every Friday and verify the folder count before clearing camera cards. #backup', 'owner'],
        ['decisions/strong-rise-rule.md', '# Strong rise rule\n\nA clip counts as a strong rise when first-day views are at least 35% above the channel average and saves are at least 20% higher. Review again after seven days. #decisions', 'owner'],
        ['ideas/products.md', '# Product ideas\n\nA compact travel journal is promising: several small shops asked for one, and current options are either bulky or hard to personalize.\n\nCompare it with [[ideas/products-2]]. #ideas #research', 'owner'],
        ['ideas/products-2.md', '# Travel journal notes\n\nA second take on the compact travel journal. Keep the map spread, removable packing list, and space for a few printed photos. #ideas', 'owner'],
        ['old/chat-log.md', '# Old chat log\n\nThe first brainstorming session is kept for context. The useful decisions were moved into [[decisions/strong-rise-rule]]. #archive', 'owner'],
        ['runs/daily-backup.md', '# Daily backup\n\nThe latest backup finished successfully. The weekly copy check found all 18 expected folders. #backup', 'run:daily-backup'],
      ]
      for (const [path, body, author] of fixtureNotes) {
        vault.set(path, body)
        const title = (body.match(/^#\s+(.+)$/m) ?? [])[1]
        const tags = [...new Set([...body.matchAll(/(?:^|\s)#([\w-]+)/g)].map(x => x[1]))]
        memoryMeta.set(path, { title, author, run_id: author.startsWith('run:') ? 'run-backup' : '', created: base, updated: base, tags })
        const id = path.replace(/[^a-z0-9]/gi, '-')
        memoryHistory.set(path, [
          { commit: `fixture-${id}`, author, date: base, message: `[${author}] write ${path}`, body },
          { commit: `fixture-old-${id}`, author, date: base, message: `[${author}] first saved ${path}`, body: `# ${title}\n\nAn earlier draft.` },
        ])
      }
      const definitions = [
        ['run-report', 'weekly-report', 'waiting'], ['run-inbox', 'inbox-triage', 'waiting'],
        ['run-tests', 'nightly-tests', 'failed'], ['run-backup', 'daily-backup', 'running'],
        ['run-research', 'market-research', 'queued'],
      ]
      for (const [run_id, env_id, status] of definitions) {
        const graph = envs.get(env_id)
        if (graph) fixedMockRuns.set(run_id, { run_id, env_id, status, started_at: base, graph, node_states: { n1: status === 'failed' ? 'failed' : status === 'waiting' ? 'waiting' : status === 'running' ? 'running' : 'pending' }, outputs: {}, waiting_on: status === 'waiting' ? 'n1' : null, usage: {} })
      }
      const claimId = '2026-10-07-calendar-claim-a1b2c3'
      if (!mockClaims.has(claimId)) mockClaims.set(claimId, { meta: { id: claimId, kind: 'capability_gap', summary: 'Need a calendar connection for this workflow.', status: 'proposed', updated: base, run_id: '' }, body: '## Problem\nNeed a calendar connection for this workflow.\n\n## Evidence\n\n## Research\n\n## Resolution\n', summaryRow() { return { id: this.meta.id, kind: this.meta.kind, summary: this.meta.summary, status: this.meta.status, updated: this.meta.updated } } })
      return send(200, { seeded: true })
    }
    if (p === '/api/assistant/settings') {
      if (req.method === 'GET') return send(200, { enabled: true, model: 'granite3.3:2b' })
      if (req.method === 'PUT') return send(200, { enabled: true, model: 'granite3.3:2b', ...(await readBody()) })
    }
    if ((m = p.match(/^\/api\/build\/interviews\/([^/]+)$/)) && req.method === 'DELETE') return send(200, { deleted: true, undo_id: commitId() })
    if (req.method === 'GET' && p === '/api/node-types') return send(200, [...NODE_CATALOG, HTTP_NODE])
    if (p === '/api/messages/threads' && req.method === 'GET') {
      const words = (url.searchParams.get('q') ?? '').toLowerCase().match(/\w+/g) ?? []
      const rows = [
        ...[...conversations].map(([id, c]) => {
          const last = c.messages.at(-1) ?? {}
          return { id: `glacier:${id}`, source: 'glacier', title: c.title || String(c.messages.find(x => x.who === 'you')?.text ?? 'Untitled conversation').slice(0, 60), last_text: last.text ?? '', last_at: last.at ?? '', unread: false, can_send: true }
        }),
        ...messageSessionRows,
        ...[...mockTeams.values()].flatMap(team => Object.entries(team.tasks).map(([taskId, task]) => {
          const title = `${team.plan.tasks.find(x => x.id === taskId)?.title ?? taskId} · ${team.plan.vision.goal}`
          const notes = task.owner_notes ?? []
          return { id: `worker:${team.team_id}:${taskId}`, source: 'worker', title, last_text: notes.at(-1)?.text ?? task.output ?? `Task ${task.status}`, last_at: notes.at(-1)?.at ?? '', unread: false, can_send: !['done', 'stopped'].includes(team.status) }
        })),
      ].filter(row => words.every(word => `${row.title} ${row.last_text} ${row.source}`.toLowerCase().includes(word)))
      return send(200, rows.sort((a, b) => b.last_at.localeCompare(a.last_at)))
    }
    if ((m = p.match(/^\/api\/messages\/threads\/([^/]+)$/)) && req.method === 'GET') {
      const id = decodeURIComponent(m[1])
      let rows = messageHistory.get(id)
      if (!rows && id.startsWith('glacier:')) {
        const conversation = conversations.get(id.slice('glacier:'.length))
        if (!conversation) return send(404, { detail: 'Conversation not found' })
        rows = conversation.messages.map((item, index) => ({ id: `${id}:${index}`, from: item.who === 'you' || item.who === 'user' ? 'me' : 'them', author: item.who === 'you' || item.who === 'user' ? 'you' : 'Glacier', text: item.text, at: item.at, kind: 'text' }))
      }
      if (!rows && id.startsWith('worker:')) {
        const [, teamId, taskId] = id.split(':')
        const team = mockTeams.get(teamId), task = team?.tasks?.[taskId]
        if (!team || !task) return send(404, { detail: 'Conversation not found' })
        rows = [...(task.owner_notes ?? []).map((note, index) => ({ id: note.id ?? `${id}:owner:${index}`, from: 'me', author: 'you', text: note.text, at: note.at, kind: 'text' })), ...(task.output ? [{ id: `${id}:output`, from: 'them', author: task.role ?? 'worker', text: task.output, at: '', kind: 'text' }] : []), ...String(team.progress_log ?? '').split('\n').filter(line => line.toLowerCase().includes(taskId.toLowerCase())).map((line, index) => ({ id: `${id}:log:${index}`, from: 'system', author: 'Glacier', text: line, at: '', kind: 'status' }))]
      }
      if (!rows) {
        const session = messageSessionRows.find(row => row.id === id)
        if (!session) return send(404, { detail: 'Conversation not found' })
        rows = messageHistory.get(id) ?? [{ id: `${id}:0`, from: 'them', author: session.source, text: session.last_text, at: session.last_at, kind: 'text' }]
      }
      const before = url.searchParams.get('before')
      rows = [...rows].sort((a, b) => b.at.localeCompare(a.at))
      if (before) {
        const cursor = rows.find(row => row.id === before)
        rows = cursor ? rows.filter(row => [row.at, row.id].join('|') < [cursor.at, cursor.id].join('|')) : rows.filter(row => row.at && row.at < before)
      }
      const messages = rows.slice(0, 50)
      return send(200, { id, messages, next_before: messages.length === 50 ? messages.at(-1).id : null })
    }
    if ((m = p.match(/^\/api\/messages\/threads\/([^/]+)$/)) && req.method === 'POST') {
      const id = decodeURIComponent(m[1]), body = await readBody()
      if (!body?.text || body.text.length > 20000) return send(400, { detail: 'text is required (max 20000 characters)' })
      const at = new Date().toISOString()
      if (id.startsWith('glacier:')) {
        const conversationId = id.slice('glacier:'.length), reply = `I can help with: ${body.text}`
        const conversation = conversations.get(conversationId) ?? { title: '', messages: [] }
        conversation.messages.push({ who: 'you', text: body.text, at }, { who: 'glacier', text: reply, at })
        conversations.set(conversationId, conversation)
        const message = { id: `${id}:${crypto.randomUUID()}`, from: 'them', author: 'Glacier', text: reply, at, kind: 'text' }
        broadcast({ type: 'messages.thread_message', thread_id: id, message })
        return send(200, { thread_id: id, message })
      }
      if (id.startsWith('worker:')) {
        const [, teamId, taskId] = id.split(':'), team = mockTeams.get(teamId), task = team?.tasks?.[taskId]
        if (!task) return send(404, { detail: 'Worker task not found' })
        const note = { id: crypto.randomUUID(), text: body.text, at }
        task.owner_notes ??= []; task.owner_notes.push(note)
        team.progress_log = `${team.progress_log ?? ''}\nOwner instruction for ${taskId}: ${body.text}`.trim()
        const message = { id: note.id, from: 'me', author: 'you', text: body.text, at, kind: 'text' }
        broadcast({ type: 'messages.thread_message', thread_id: id, message })
        return send(200, { thread_id: id, message })
      }
      const session = messageSessionRows.find(row => row.id === id)
      if (!session) return send(404, { detail: 'Conversation not found' })
      if (!session.can_send) return send(403, { detail: session.can_send_reason || 'This conversation is read-only' })
      const message = { id: `${id}:${crypto.randomUUID()}`, from: 'them', author: session.source, text: `${session.source} reply: ${body.text}`, at, kind: 'text' }
      messageHistory.set(id, [message, ...(messageHistory.get(id) ?? [])])
      session.last_text = message.text; session.last_at = at
      broadcast({ type: 'messages.thread_message', thread_id: id, message })
      return send(200, { thread_id: id, message })
    }
    if (p === '/api/messages/threads' && req.method === 'POST') {
      const body = await readBody()
      if (!body?.text || !['glacier', 'codex', 'claude'].includes(body.source)) return send(400, { detail: 'source must be glacier, codex, or claude' })
      const id = body.source === 'glacier' ? crypto.randomUUID() : `mock-${crypto.randomUUID()}`
      const threadId = body.source === 'glacier' ? `glacier:${id}` : body.source === 'claude' ? `claude-code:${id}` : `codex:${id}`
      const at = new Date().toISOString(), reply = body.source === 'glacier' ? `I can help with: ${body.text}` : `${body.source} reply: ${body.text}`
      const message = { id: `${threadId}:${crypto.randomUUID()}`, from: 'them', author: body.source === 'glacier' ? 'Glacier' : body.source, text: reply, at, kind: 'text' }
      if (body.source === 'glacier') conversations.set(id, { title: '', messages: [{ who: 'you', text: body.text, at }, { who: 'glacier', text: reply, at }] })
      else { const row = { id: threadId, source: body.source, title: body.text.slice(0, 60), last_text: reply, last_at: at, unread: false, can_send: true }; messageSessionRows.unshift(row); messageHistory.set(threadId, [message]) }
      broadcast({ type: 'messages.thread_message', thread_id: threadId, message })
      return send(200, { thread: { id: threadId, source: body.source, title: body.text.slice(0, 60), last_text: reply, last_at: at, unread: false, can_send: true }, thread_id: threadId, message })
    }
    if (p.startsWith('/api/assistant/conversations')) {
      const titleOf = c => c.title || (c.messages.find(x => x.who === 'you')?.text ?? '').split(/\s+/).join(' ').slice(0, 60) || 'Untitled conversation'
      if (req.method === 'GET' && p === '/api/assistant/conversations') {
        const words = (url.searchParams.get('q') ?? '').toLowerCase().match(/\w+/g) ?? []
        return send(200, [...conversations].map(([id, c]) => ({ id, title: titleOf(c), updated: c.messages.at(-1)?.at ?? '', messages: c.messages.length, text: [titleOf(c), ...c.messages.map(x => x.text)].join(' ').toLowerCase() }))
          .filter(x => words.every(w => x.text.includes(w))).map(({ text, ...x }) => x).sort((a, b) => b.updated.localeCompare(a.updated)))
      }
      const cm = p.match(/^\/api\/assistant\/conversations\/([^/]+)(\/rename|\/undo-delete)?$/)
      const id = cm && decodeURIComponent(cm[1])
      const c = id && conversations.get(id)
      if (cm && req.method === 'DELETE' && !cm[2]) {
        if (!c) return send(404, { detail: 'Conversation not found' })
        const path = `conversations/${id}.md`, commit = commitId()
        deletedConversations.set(id, { conversation: c, body: vault.get(path), commit })
        conversations.delete(id); vault.delete(path)
        return send(200, { deleted: true, id, commit })
      }
      if (cm && req.method === 'POST' && cm[2] === '/undo-delete') {
        const body = await readBody(), deleted = deletedConversations.get(id)
        if (!deleted || !String(body?.commit ?? '').startsWith(deleted.commit)) return send(404, { detail: 'Conversation not found' })
        conversations.set(id, deleted.conversation); vault.set(`conversations/${id}.md`, deleted.body); deletedConversations.delete(id)
        return send(200, { restored: true, commit: commitId() })
      }
      if (!c) return send(404, { detail: 'Conversation not found' })
      if (req.method === 'GET' && !cm[2]) return send(200, { id: cm[1], title: titleOf(c), messages: c.messages })
      if (req.method === 'POST' && cm[2] === '/rename') {
        const title = String((await readBody())?.title ?? '').trim()
        if (!title || title.length > 80 || /[\r\n]/.test(title)) return send(400, { detail: 'Title must be 1 to 80 characters with no line breaks' })
        c.title = title; return send(200, { id: cm[1], title, commit: commitId() })
      }
    }
    if (req.method === 'POST' && p === '/api/assistant/chat') {
      const body = await readBody()
      if (!body?.message) return send(400, { detail: 'message is required' })
      const conversationId = body.conversation_id ?? crypto.randomUUID()
      const runId = crypto.randomUUID()
      const messageId = crypto.randomUUID()
      res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' })
      const emit = (type, data = {}) => res.write(`data: ${JSON.stringify({ type, ...data })}\n\n`)
      emit('RUN_STARTED', { threadId: conversationId, runId })
      const runMatch = body.message.match(/^\s*run\s+my\s+(.+?)\s+now[.!?\s]*$/i)
      if (runMatch) {
        const flow = [...envs.values()].find(e => String(e.name).toLowerCase() === runMatch[1].toLowerCase())
        const reply = flow ? `Run ${flow.name} now?` : `I could not find an automation named ${runMatch[1]}. Check its name and try again.`
        if (flow) {
          const id = crypto.randomUUID()
          const proposal = { id, conversation_id: conversationId, run_existing: true, flow: { id: flow.id, name: flow.name }, explanation: reply }
          assistantProposals.set(id, proposal)
          const toolCallId = crypto.randomUUID()
          emit('TEXT_MESSAGE_START', { messageId, role: 'assistant' })
          emit('TOOL_CALL_START', { toolCallId, toolCallName: 'propose_run', parentMessageId: messageId })
          emit('TOOL_CALL_ARGS', { toolCallId, delta: JSON.stringify(proposal) })
          emit('TOOL_CALL_END', { toolCallId })
        } else emit('TEXT_MESSAGE_START', { messageId, role: 'assistant' })
        emit('TEXT_MESSAGE_CONTENT', { messageId, delta: reply }); emit('TEXT_MESSAGE_END', { messageId })
        emit('RUN_FINISHED', { threadId: conversationId, runId })
        return res.end()
      }
      const automation = /make me|automate|every day|daily|refine this automation proposal/i.test(body.message)
      const uiChange = /change (?:glacier'?s? )?(?:own )?ui|change this screen|update this screen|update the screen/i.test(body.message)
      let reply = body.screen
        ? `You're on ${body.screen}${body.focus ? `, looking at ${body.focus}` : ''}. I can help with this screen. ${body.message}`
        : `I can help with: ${body.message}`
      if (uiChange) {
        const id = crypto.randomUUID()
        const proposal = { id, conversation_id: conversationId, kind: 'ui_change',
          explanation: 'I prepared a small screen change for your review.',
          diff: '--- a/glacier/web/src/App.tsx\n+++ b/glacier/web/src/App.tsx\n@@ -1 +1 @@\n-old\n+new\n',
          files: ['glacier/web/src/App.tsx'], related_spec: 'glacier/web/e2e/shell.spec.mjs',
          mock_fail: /fail checks/i.test(body.message) }
        assistantProposals.set(id, proposal)
        const toolCallId = crypto.randomUUID()
        emit('TEXT_MESSAGE_START', { messageId, role: 'assistant' })
        emit('TOOL_CALL_START', { toolCallId, toolCallName: 'propose_ui_change', parentMessageId: messageId })
        emit('TOOL_CALL_ARGS', { toolCallId, delta: JSON.stringify(proposal) })
        emit('TOOL_CALL_END', { toolCallId })
        reply = `${proposal.explanation} It has not been applied.`
      }
      if (automation) {
        const id = crypto.randomUUID()
        const focusId = String(body.focus || '')
        const flowId = /^[a-z0-9][a-z0-9-]{0,79}$/.test(focusId) && focusId !== 'new-flow'
          ? focusId : body.message.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'new-flow'
        const refined = /refine this automation proposal/i.test(body.message)
        const flow = { id: flowId, name: 'Inbox summary', goal: 'Make me a daily inbox summary', created_by: 'assistant',
          nodes: [
            { id: 'fetch', type: 'command', config: { cmd: 'echo fetch inbox' }, position: { x: 60, y: 60 } },
            { id: 'summarize', type: 'codex', config: { prompt: 'Summarize the inbox' }, position: { x: 320, y: 60 } },
            ...(refined ? [{ id: 'review', type: 'approval', config: { prompt: 'Review the summary' }, position: { x: 580, y: 60 } }] : []),
          ],
          edges: [ { id: 'e1', source: 'fetch', target: 'summarize', label: '' }, ...(refined ? [{ id: 'e2', source: 'summarize', target: 'review', label: '' }] : []) ],
          acceptance: [{ kind: 'human', question: 'Is the inbox summary useful?' }] }
        const proposal = { id, conversation_id: conversationId, flow, explanation: 'A flow for your inbox summary.', problems: [],
          step_order: flow.nodes.map(node => node.id), step_notes: Object.fromEntries(flow.nodes.map(node => [node.id, Object.values(node.config)[0]])) }
        assistantProposals.set(id, proposal)
        const toolCallId = crypto.randomUUID()
        emit('TEXT_MESSAGE_START', { messageId, role: 'assistant' })
        emit('TOOL_CALL_START', { toolCallId, toolCallName: 'propose_flow', parentMessageId: messageId })
        emit('TOOL_CALL_ARGS', { toolCallId, delta: JSON.stringify(proposal) })
        emit('TOOL_CALL_END', { toolCallId })
        reply = proposal.explanation
      }
      if (!automation && !uiChange) emit('TEXT_MESSAGE_START', { messageId, role: 'assistant' })
      if (reply) emit('TEXT_MESSAGE_CONTENT', { messageId, delta: reply })
      emit('TEXT_MESSAGE_END', { messageId })
      const conv = conversations.get(conversationId) ?? { title: '', messages: [] }
      const at = new Date().toISOString()
      conv.messages.push({ who: 'you', text: body.message, at }, { who: 'glacier', text: reply, at }); conversations.set(conversationId, conv)
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
      if (proposal.kind === 'ui_change') {
        assistantProposals.delete(proposal.id)
        const passed = !proposal.mock_fail
        return send(200, { applied: true, branch: `assistant/ui-change/${proposal.id}`,
          worktree: `/worktrees/ui-changes/${proposal.id}`, changed_files: proposal.files ?? ['glacier/web/src/App.tsx'],
          checks: ['tsc', 'theme lint', 'build', 'e2e'], passed,
          check_results: { tsc: { passed }, 'theme lint': { passed: true }, build: { passed: true }, e2e: { passed } } })
      }
      const flow = proposal.flow
      if (proposal.run_existing) {
        if (!body.run_now) return send(400, { detail: 'Confirm that you want to run this automation' })
        assistantProposals.delete(proposal.id)
        return send(200, { saved: false, run_id: startRun(envs.get(flow.id)), status: 'running' })
      }
      if (envs.has(flow.id)) return send(409, { detail: 'A flow with this name already exists' })
      const bad = flow.nodes.map(node => node.type).filter(type => type !== HTTP_NODE.type && !NODE_CATALOG.some(item => item.type === type))
      if (bad.length) return send(400, { detail: `unknown node types: ${bad}` })
      if (flow.goal && !flow.acceptance?.length) return send(400, { detail: 'This goal has no check yet. Add a way to check it is done before running it.' })
      envs.set(flow.id, flow)
      const commit = commitId()
      vault.set(`environments/${flow.id}.json`, JSON.stringify(flow, null, 2))
      assistantProposals.delete(proposal.id)
      const undo_id = crypto.randomUUID()
      if (body.run_now) return send(200, { saved: true, commit, undo_id, run_id: startRun(flow), status: 'running' })
      return send(200, { saved: true, commit, undo_id })
    }
    // ---- settings (screen development only) ----
    if (p === '/api/secrets' && req.method === 'GET') return send(200, [...mockSecrets].sort())
    if ((m = p.match(/^\/api\/secrets\/([A-Za-z0-9_.-]+)$/))) {
      if (req.method === 'PUT') { const b = await readBody(); if (!b?.value) return send(422, { detail: 'value required' }); mockSecrets.add(m[1]); return send(200, { saved: true }) }
      if (req.method === 'DELETE') { mockSecrets.delete(m[1]); return send(200, { deleted: true }) }
    }
    if (p === '/api/releases/current' && req.method === 'GET') return send(200, { version: '0.2.0', markdown: '# Glacier 0.2.0\n\n- Mock release notes.' })
    if (p === '/api/releases/installed/seen' && req.method === 'GET') return send(200, { version: mockSeenVersion })
    if (p === '/api/releases/installed/seen' && req.method === 'PUT') { const b = await readBody(); mockSeenVersion = String(b.version || ''); return send(200, { version: mockSeenVersion }) }
    if (p === '/api/costs') return send(200, { total_usd: 0, paid_cap_usd: 0, local_share: 0.8, by_route: [], by_model: [{ model: 'qwen3:0.6b', runs: 12, steps: 40, tokens_in: 52000, tokens_out: 9000, cost_usd: 0 }] })
    if (p === '/api/memory/compat') return send(200, { ok: true, notes_checked: vault.size, problems: [] })
    if (p === '/api/system/settings') return send(200, { mode: 'standard', local_model: 'qwen3:0.6b', max_parallel_runs: 2, ask_route: 'local', ask_route_reason: 'Codex is unavailable or signed out, so Ask will use Ollama on this computer.' })
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
    if (p === '/api/files' && req.method === 'GET') return send(200, [...uploadedFiles.values()])
    if (p === '/api/files' && req.method === 'DELETE') {
      const project = url.searchParams.get('project'), name = url.searchParams.get('name'), key = `${project}/${name}`
      const file = uploadedFiles.get(key); if (!file) return send(404, { detail: 'Uploaded file not found' })
      const undo_id = crypto.randomBytes(16).toString('hex'); deletedFiles.set(undo_id, file); uploadedFiles.delete(key)
      return send(200, { deleted: true, undo_id, name, project })
    }
    if (p === '/api/files/undo-delete' && req.method === 'POST') {
      const body = await readBody(), file = deletedFiles.get(body?.undo_id)
      if (!file) return send(404, { detail: 'Removed file not found' })
      uploadedFiles.set(`${file.project}/${file.name}`, file); deletedFiles.delete(body.undo_id)
      return send(200, { restored: true, name: file.name, project: file.project })
    }
    if (p === '/api/starter' && req.method === 'GET') return send(200, { applied: starterApplied, mode: 'standard', local_model: 'granite3.3:2b',
      reason: 'Your computer has enough memory for Glacier\'s standard mode.',
      coding_agents_found: [{ id: 'codex', name: 'Codex', found: true, version: '0.1', usable_as_step: true }, { id: 'acp-opencode', name: 'OpenCode', found: false, version: '', usable_as_step: false }],
      suggested_automations: [{ template_id: 'tpl-daily-report', name: 'Daily report', why: 'All tools and models this automation needs are available on your computer.', requires_local_model: true },
        { template_id: 'tpl-folder-backup', name: 'Folder backup', why: 'Needs nothing extra.', requires_local_model: false }],
      missing_but_useful: [{ name: 'OpenCode', why: 'Another free coding agent Glacier can use as a step.', license: 'MIT', download_page: 'https://opencode.ai' }] })
    if (p === '/api/starter/apply' && req.method === 'POST') { const b = await readBody(); starterApplied = true
      return send(200, { created: (b.template_ids ?? []).map(t => ({ template_id: t, id: t.replace(/^tpl-/, ''), name: t.replace(/^tpl-/, '').replace(/-/g, ' ') })), mode: b.mode, local_model: 'granite3.3:2b' }) }
    if (p === '/api/sessions' && req.method === 'GET') return send(200, [
      { id: 'opencode:ses_demo', tool: 'opencode', source: 'opencode', started: new Date(Date.now() - 72e5).toISOString(), updated: new Date(Date.now() - 6e5).toISOString(), title: 'Fix the login page', cwd: '/home/me/site', active: false },
      { id: 'codex-demo', tool: 'codex', started: new Date(Date.now() - 864e5).toISOString(), updated: new Date(Date.now() - 36e5).toISOString(), title: 'Add tests for the parser', cwd: '/home/me/parser', active: true }])
    if ((m = p.match(/^\/api\/sessions\/([^/]+)$/)) && req.method === 'GET') return send(200, { id: decodeURIComponent(m[1]), tool: 'opencode', source: 'opencode', started: new Date(Date.now() - 72e5).toISOString(), updated: new Date().toISOString(), title: 'Fix the login page', cwd: '/home/me/site', active: false,
      events: [{ type: 'user_message', text: 'The login button does nothing' }, { type: 'command', text: 'Ran command: npm test' }, { type: 'assistant_message', text: 'Fixed the click handler and added a test.' }] })
    if ((m = p.match(/^\/api\/sessions\/([^/]+)\/save-to-memory$/)) && req.method === 'POST') return send(200, { saved: true, path: 'sessions/opencode_ses_demo-abc.md' })
    if (p === '/api/imports/refresh' && req.method === 'POST') return send(200, { chatgpt: { added: 2, updated: 1, unchanged: 145 } })
    if ((p === '/api/files' || p === '/api/imports') && req.method === 'POST') {
      let size = 0; await new Promise(r => { req.on('data', c => (size += c.length)); req.on('end', r) })
      if (p === '/api/files') {
        const file = { name: `upload-${uploadedFiles.size + 1}.txt`, project: 'Inbox', size, path: `files/Inbox/upload-${uploadedFiles.size + 1}.txt`, note: null }
        uploadedFiles.set(`${file.project}/${file.name}`, file)
        return send(200, { ...file, duplicate: false })
      }
      return send(200, { conversations: 3, notes: 3 })
    }
    // ---- claims + templates (screen development only) ----
    if ((m = p.match(/^\/api\/claims\/([^/]+)\/undo-delete$/)) && req.method === 'POST') {
      const body = await readBody(), claim = deletedClaims.get(m[1])
      if (!claim || !String(body?.commit ?? '').startsWith(claim.commit)) return send(404, { detail: 'claim not found' })
      mockClaims.set(m[1], claim.value); deletedClaims.delete(m[1])
      return send(200, { restored: true, commit: commitId() })
    }
    if ((m = p.match(/^\/api\/claims\/([^/]+)$/)) && req.method === 'DELETE') {
      const claim = mockClaims.get(m[1]); if (!claim) return send(404, { detail: 'claim not found' })
      const commit = commitId(); deletedClaims.set(m[1], { value: claim, commit }); mockClaims.delete(m[1])
      return send(200, { deleted: true, id: m[1], commit })
    }
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
    if ((m = p.match(/^\/api\/claims\/([^/]+)\/rerun$/)) && req.method === 'POST') {
      const c = mockClaims.get(m[1]); if (!c) return send(404, { detail: 'claim not found' })
      if (!c.meta.run_id) return send(400, { detail: 'This claim did not come from a run, so there is nothing to run again.' })
      if (!envs.has('nightly-sync')) envs.set('nightly-sync', { id: 'nightly-sync', name: 'Nightly sync', nodes: [{ id: 'fetch', type: 'command', config: { cmd: 'echo ok' }, position: { x: 0, y: 0 } }], edges: [] })
      const run_id = startRun(envs.get('nightly-sync')); c.body += `\n- Owner ran the flow again to check: run ${run_id}.`
      return send(200, { run_id, env_id: 'nightly-sync' })
    }
    if (p === '/api/templates' && req.method === 'GET') return send(200, mockTemplates)
    if (p === '/api/templates/undo-delete' && req.method === 'POST') {
      const body = await readBody(), item = deletedTemplates.get(body?.undo_id)
      if (!item) return send(404, { detail: 'Removed template not found' })
      mockTemplates.push(item); deletedTemplates.delete(body.undo_id)
      return send(200, { restored: true, id: item.id })
    }
    if ((m = p.match(/^\/api\/templates\/([^/]+)$/)) && req.method === 'DELETE') {
      const index = mockTemplates.findIndex(item => item.id === decodeURIComponent(m[1]) && item.review_status === 'approved')
      if (index < 0) return send(404, { detail: 'Imported template not found' })
      const [item] = mockTemplates.splice(index, 1), undo_id = crypto.randomBytes(16).toString('hex')
      deletedTemplates.set(undo_id, item)
      return send(200, { deleted: true, id: item.id, undo_id })
    }
    if ((m = p.match(/^\/api\/environments\/([^/]+)\/undo-delete$/)) && req.method === 'POST') {
      const id = decodeURIComponent(m[1]), body = await readBody(), deleted = deletedFlows.get(id)
      if (!deleted || !String(body?.commit ?? '').startsWith(deleted.commit)) return send(404, { detail: 'Removed flow not found' })
      envs.set(id, deleted.flow); vault.set(deleted.path, deleted.body); deletedFlows.delete(id)
      return send(200, { restored: true, commit: commitId() })
    }
    if (req.method === 'GET' && p === '/api/environments') return send(200, [...envs.values()].map(e => ({ id: e.id, name: e.name, enabled: e.enabled })))
    if ((m = p.match(/^\/api\/environments\/([^/]+)$/))) {
      const id = decodeURIComponent(m[1])
      if (req.method === 'GET') return envs.has(id) ? send(200, envs.get(id)) : send(404, { detail: 'environment not found' })
      if (req.method === 'DELETE') {
        const flow = envs.get(id); if (!flow) return send(404, { detail: 'Flow not found' })
        const epath = `environments/${id}.json`, body = vault.get(epath), commit = commitId()
        deletedFlows.set(id, { flow, path: epath, body, commit }); envs.delete(id); vault.delete(epath)
        return send(200, { deleted: true, id, commit })
      }
      if (req.method === 'PUT') {
        const body = await readBody()
        if (!body || !Array.isArray(body.nodes) || !Array.isArray(body.edges)) return send(422, { detail: 'invalid environment' })
        const bad = body.nodes.map(n => n.type).filter(t => t !== HTTP_NODE.type && !NODE_CATALOG.some(c => c.type === t) && !['file_trigger', 'webhook_trigger'].includes(t))
        if (bad.length) return send(400, { detail: `unknown node types: ${bad}` })
        envs.set(id, { ...body, id })
        const commit = commitId(), epath = `environments/${id}.json`, text = JSON.stringify({ ...body, id }, null, 2)
        vault.set(epath, text)
        const eh = memoryHistory.get(epath) ?? []; eh.unshift({ commit, author: 'owner', date: new Date().toISOString(), message: `[owner] write ${epath}`, body: text }); memoryHistory.set(epath, eh)
        return send(200, { saved: true, commit })
      }
    }
    if (req.method === 'POST' && (m = p.match(/^\/api\/environments\/([^/]+)\/restore$/))) {
      const id = decodeURIComponent(m[1]), epath = `environments/${id}.json`, body = await readBody()
      const old = (memoryHistory.get(epath) ?? []).find(h => h.commit === body?.commit)
      if (!old) return send(400, { detail: 'Saved version was not found for this flow.' })
      const flow = JSON.parse(old.body); envs.set(id, flow); vault.set(epath, old.body)
      const commit = commitId(); memoryHistory.get(epath).unshift({ commit, author: 'owner', date: new Date().toISOString(), message: `[owner] restore ${epath}`, body: old.body })
      return send(200, { restored: true, new_commit: commit })
    }
    if (req.method === 'POST' && (m = p.match(/^\/api\/environments\/([^/]+)\/run$/))) {
      const id = decodeURIComponent(m[1])
      if (!envs.has(id)) return send(404, { detail: 'environment not found' })
      return send(200, { run_id: startRun(envs.get(id)) })
    }
    if (req.method === 'GET' && p === '/api/runs') {
      const envId = url.searchParams.get('env_id')
      const list = [...runs.values(), ...fixedMockRuns.values()].filter(r => !hiddenRuns.has(r.run_id) && (!envId || r.env_id === envId))
        .sort((a, b) => b.started_at.localeCompare(a.started_at))
        .map(r => ({ run_id: r.run_id, env_id: r.env_id, status: r.status, started_at: r.started_at }))
      return send(200, list)
    }
    if ((m = p.match(/^\/api\/runs\/([^/]+)\/undo-delete$/)) && req.method === 'POST') {
      const id = decodeURIComponent(m[1]); if (!hiddenRuns.has(id)) return send(404, { detail: 'Removed run not found' })
      hiddenRuns.delete(id); return send(200, { restored: true, run_id: id })
    }
    if ((m = p.match(/^\/api\/runs\/([^/]+)$/)) && req.method === 'DELETE') {
      const id = decodeURIComponent(m[1]), run = runs.get(id); if (!run) return send(404, { detail: 'Run not found' })
      if (['running', 'waiting', 'queued', 'pending'].includes(run.status)) return send(409, { detail: 'A run that is still active cannot be removed from history' })
      hiddenRuns.add(id); return send(200, { deleted: true, run_id: id })
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
      const id = decodeURIComponent(m[1]), r = runs.get(id) ?? fixedMockRuns.get(id)
      return r ? send(200, publicRun(r)) : send(404, { detail: 'run not found' })
    }
    if (req.method === 'GET' && (m = p.match(/^\/api\/runs\/([^/]+)\/explain$/))) {
      const id = decodeURIComponent(m[1]), r = runs.get(id) ?? fixedMockRuns.get(id)
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
      const id = decodeURIComponent(m[1])
      if (id === 'run-dispatch-waiting') { mockApprovalDone = true; return send(200, { ok: true }) }
      const r = runs.get(id) ?? fixedMockRuns.get(id)
      if (!r) return send(404, { detail: 'run not found' })
      const body = await readBody()
      if (!body || r.waiting_on !== body.node_id) return send(409, { detail: 'run is not waiting on that node' })
      if (r.resolve) r.resolve(body.approved === true)
      else {
        r.waiting_on = null
        r.status = body.approved === true ? 'done' : 'rejected'
        r.node_states[body.node_id] = body.approved === true ? 'done' : 'skipped'
      }
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
  const startNode = r.graph.nodes.find(n => ['schedule', 'file_trigger', 'webhook_trigger'].includes(n.type))
  return { run_id: r.run_id, env_id: r.env_id, status: r.status, node_states: r.node_states, outputs: r.outputs, waiting_on: r.waiting_on,
    ...(startNode ? { trigger: { type: startNode.type === 'schedule' ? 'schedule' : startNode.type === 'file_trigger' ? 'file' : 'webhook', node_id: startNode.id } } : {}) }
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
  const forEachItems = new Map()
  const forEachIndex = new Map()
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
      case 'http_request': {
        const status = String(c.expect_status ?? '2xx') === '201' || c.method === 'POST' ? 201 : 200
        const output = `Status: ${status}\n\n${JSON.stringify({ message: 'mock response', saved: true }, null, 2)}\n`
        result = { exit_code: 0, output }
        setState(r, id, 'done', output)
        break
      }
      case 'json_transform': {
        let value
        try { value = JSON.parse(prev?.output ?? 'null') } catch { value = null }
        let outValue = value
        try {
          const extra = JSON.parse(c.data || '{}')
          if (c.operation === 'set_fields') outValue = { ...(value && !Array.isArray(value) ? value : {}), ...JSON.parse(c.fields || '{}') }
          else if (c.operation === 'filter') outValue = (Array.isArray(value) ? value : []).filter(row => String(row?.[c.field]) === String(c.equals))
          else if (c.operation === 'merge') outValue = value == null ? extra : Array.isArray(value) && Array.isArray(extra) ? [...value, ...extra] : { ...(value || {}), ...(extra || {}) }
          else if (c.operation === 'split') outValue = Array.isArray(value) ? value : value?.items ?? []
          else if (c.operation === 'dedupe') { const seen = new Set(); outValue = (Array.isArray(value) ? value : []).filter(row => { const v = JSON.stringify(c.key ? row?.[c.key] : row); if (seen.has(v)) return false; seen.add(v); return true }) }
        } catch { outValue = value }
        result = { exit_code: 0, output: JSON.stringify(outValue) }
        setState(r, id, 'done', result.output)
        break
      }
      case 'data_table':
        result = { exit_code: 0, output: c.operation === 'query' ? '[]' : 'Saved one row' }
        setState(r, id, 'done', result.output)
        break
      case 'csv_file':
        result = { exit_code: 0, output: c.operation === 'write' ? 'Wrote CSV file' : '[]' }
        setState(r, id, 'done', result.output)
        break
      case 'delay':
        result = { exit_code: 0, output: prev?.output ?? 'Wait finished' }
        setState(r, id, 'done', result.output)
        break
      case 'structured_ai': {
        const output = JSON.stringify({ mock: true, input: prev?.output ?? '' })
        result = { exit_code: 0, output }
        setState(r, id, 'done', output)
        break
      }
      case 'email_send': {
        if ((c.draft_only ?? 'Yes') === 'Yes') result = { exit_code: 0, output: 'Draft saved in this flow folder' }
        else if (String(prev?.output ?? '').toLowerCase().includes('approved')) result = { exit_code: 0, output: `Email sent to ${c.to ?? ''}` }
        else result = { exit_code: 1, output: 'Add an approval step before sending.' }
        setState(r, id, result.exit_code ? 'failed' : 'done', result.output)
        if (result.exit_code && !handledByCheck(id)) { failed = true; queue.length = 0; next = [] }
        break
      }
      case 'email_read':
        result = { exit_code: 0, output: '[]' }
        setState(r, id, 'done', result.output)
        break
      case 'email_trigger': {
        const output = JSON.stringify({ message_id: '<mock@example.test>', from: 'person@example.test', subject: 'Mock email', body: 'Example message' })
        result = { exit_code: 0, output }
        setState(r, id, 'done', output)
        break
      }
      case 'for_each': {
        if (!forEachItems.has(id)) {
          let items
          try { items = JSON.parse(prev?.output ?? 'null') } catch { items = null }
          const maxItems = Math.max(1, Math.min(Number(c.max_items) || 100, MAX_LOOP))
          if (!Array.isArray(items)) {
            result = { exit_code: 1, output: 'For each item needs a JSON list from the previous step' }
            setState(r, id, 'failed', result.output)
            if (!handledByCheck(id)) { failed = true; queue.length = 0; next = [] }
            break
          }
          if (items.length > maxItems) {
            result = { exit_code: 1, output: `This list has ${items.length} items, above the limit of ${maxItems}` }
            setState(r, id, 'failed', result.output)
            if (!handledByCheck(id)) { failed = true; queue.length = 0; next = [] }
            break
          }
          forEachItems.set(id, items)
          forEachIndex.set(id, 0)
        }
        const items = forEachItems.get(id)
        const index = forEachIndex.get(id)
        if (index < items.length) {
          result = { exit_code: 0, output: JSON.stringify(items[index]) }
          forEachIndex.set(id, index + 1)
          setState(r, id, 'running', result.output)
          next = out(id).filter(e => e.label === 'each')
        } else {
          result = { exit_code: 0, output: `Processed ${items.length} items` }
          setState(r, id, 'done', result.output)
          forEachItems.delete(id); forEachIndex.delete(id)
          next = out(id).filter(e => e.label === 'done')
        }
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

server.listen(PORT, () => console.log(`glacier mock api on http://localhost:${server.address().port}`))
