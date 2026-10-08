// Screenshot every screen with sample data, for side-by-side comparison with docs/ui/mockup.png.
// usage (from glacier/web, after vite build): node e2e/screenshots.mjs dist <outPrefix> home automations ask memory settings/system
import { chromium } from 'playwright'
import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
const [dist, out, ...hashes] = process.argv.slice(2)
const now = Date.now(), h = n => new Date(now - n * 3600e3).toISOString()
const F = {
  '/api/home': { local_ai: { online: true, model: 'qwen3:0.6b' }, counts: { running: 1, need_you: 3 },
    needs_you: [
      { kind: 'approval', title: 'approval waiting', detail: 'marketing flow update', at: h(2), ref: { env_id: 'marketing', run_id: 'r1' } },
      { kind: 'claim', title: 'claim to review', detail: 'research results', at: h(4), ref: { claim_id: 'c1' } },
      { kind: 'failed_run', title: 'failed run', detail: 'backup documents', at: h(6), ref: { env_id: 'backup', run_id: 'r2' } }],
    running: [{ run_id: 'r3', env_id: 'website-monitor', name: 'website monitor', status: 'running', step: 2, steps: 4, started_at: h(0.1) },
              { run_id: 'r4', env_id: 'daily-summary', name: 'daily summary', status: 'queued', step: 0, steps: 3, started_at: h(0) }],
    recent_notes: [{ path: 'ideas/products.md', summary: 'added product ideas to memory', at: h(3) }, { path: 'flows/social.md', summary: 'updated flow: social media', at: h(5) }] },
  '/api/environments': [{ id: 'daily-summary', name: 'daily summary' }, { id: 'website-monitor', name: 'website monitor' }, { id: 'backup', name: 'backup documents' }, { id: 'social', name: 'social media posts' }, { id: 'research', name: 'research assistant' }],
  '/api/runs/r3': { run_id: 'r3', env_id: 'website-monitor', status: 'running', waiting_on: null,
    node_states: { n1: 'done', n2: 'done', n3: 'running', n4: 'pending' },
    outputs: { n3: '[1:24:01] Fetching website...\n[1:24:03] Checking for changes...\n[1:24:05] Changes detected: 2\n[1:24:06] Analyzing content...' },
    usage: { n3: { model: 'qwen3:0.6b', route: 'local/ollama', tokens_in: 900, tokens_out: 340, cost_usd: 0 } },
    verification: [{ check: 0, kind: 'website accessible', passed: true, evidence: 'HTTP 200' }, { check: 1, kind: 'changes detected', passed: true, evidence: '2 changes' }], verified: null },
  '/api/runs/r3/changes': [{ path: 'monitor/changes.md', commit: 'a1b2c3d4', author: 'run', repo: 'vault' }, { path: 'monitor/log.md', commit: 'a1b2c3d4', author: 'run', repo: 'vault' }],
  '/api/runs': [{ run_id: 'r3', env_id: 'website-monitor', status: 'running', started_at: h(0.1) }, { run_id: 'r5', env_id: 'website-monitor', status: 'done', started_at: h(6) },
    { run_id: 'r6', env_id: 'website-monitor', status: 'failed', started_at: h(18) }, { run_id: 'r7', env_id: 'website-monitor', status: 'done', started_at: h(30) }],
  '/api/memory/notes': [{ path: 'ideas/products.md', title: 'Product ideas', author: 'assistant', updated: h(3), tags: ['projects'] }, { path: 'people/sam.md', title: 'Sam', author: 'you', updated: h(30), tags: ['people'] }, { path: 'prefs.md', title: 'Preferences', author: 'you', updated: h(80), tags: ['preferences'] }],
  '/api/memory/note': { path: 'ideas/products.md', body: '# Product ideas\n\n- pixel desk lamp\n- glacier mug\n\nSee [[people/sam]].', meta: { title: 'Product ideas' }, links_out: ['people/sam'], links_in: [] },
  '/api/memory/history': [{ commit: 'a1b2c3d4', author: 'assistant', date: h(3), message: 'added product ideas' }],
  '/api/system/check': { cpu_cores: 8, memory_gb: 16, disk_free_gb: 120, ollama_models: ['qwen3:0.6b'], tools: { codex: { found: true, version: '0.9' }, ollama: { found: true, version: '0.12' }, git: { found: true, version: '2.42.0' } }, recommended: { mode: 'standard', local_model: 'qwen3:0.6b', max_parallel_runs: 4 }, messages: [] },
  '/api/claims': [{ id: 'c1042', kind: 'research', summary: 'Best eBay product opportunities', status: 'proposed', assigned_to: null, updated: h(4) }],
  '/api/claims/c1042': { meta: { id: 'c1042', kind: 'research needed', summary: 'Best eBay product opportunities', status: 'proposed', updated: h(4) },
    body: '## Problem\nBest eBay product opportunities\n\n## Evidence\n- completed successfully\n- 5 product ideas generated\n- sources included\n\n## Research\n- analyzed 12 categories\n- found 5 high-demand products\n- checked competition and pricing\n\n## Proposal\n- used web research agent\n- checked recent sales data\n- compared supplier costs\n\n## Resolution\n' },
  '/api/templates': [['Email monitor', 'Check and summarize important emails'], ['Daily summary', 'Get a daily overview of what matters'], ['Website monitor', 'Track changes on any website'], ['Social media', 'Create and schedule posts'], ['Research assistant', 'Deep research with verified sources'], ['File organizer', 'Sort and organize files automatically']]
    .map(([n, d], i) => { const id = ['tpl-inbox-triage','tpl-daily-report','tpl-website-monitor','tpl-test-and-fix','tpl-weekly-research','tpl-downloads-tidy'][i]; return { id, name: n, description: d, author: 'Glacier', license: 'Apache-2.0', review_status: 'reviewed', installable: true, template: { id, name: n, nodes: [{ id: 'a', type: 'schedule', config: {}, position: { x: 0, y: 0 } }, { id: 'b', type: 'command', config: {}, position: { x: 0, y: 0 } }], edges: [] } } }),
  '/api/memory/graph': (() => { const n = [], e = []; const t = ['Projects', 'Notes', 'Preferences', 'Conversations', 'People', 'Docs'];
    t.forEach((x, i) => { n.push({ id: `hub/${i}`, title: x, kind: 'note', author: 'you' }); e.push({ source: `hub/${i}`, target: 'you', kind: 'wrote' }) })
    for (let i = 0; i < 60; i++) { const k = i % 9 === 0 ? 'run' : i % 13 === 0 ? 'flow' : 'note'; n.push({ id: `n/${i}`, title: `note ${i}`, kind: k, author: i % 2 ? 'assistant' : 'you' }); e.push({ source: `n/${i}`, target: `hub/${i % 6}`, kind: 'link' }); e.push({ source: `n/${i}`, target: i % 2 ? 'assistant' : 'you', kind: 'wrote' }) }
    return { nodes: n, edges: e } })(),
  '/api/memory/hygiene': [{ id: 'h1', kind: 'merge', paths: ['ideas/products.md', 'ideas/products-2.md'], reason: 'These two notes say almost the same thing.' },
    { id: 'h2', kind: 'archive', paths: ['logs/chat-2026-03.md'], reason: 'Old chat log, not opened or linked for over 90 days.' },
    { id: 'h3', kind: 'merge', paths: ['people/sam.md', 'people/sam-k.md', 'people/samuel.md'], reason: 'Three notes about the same person.' }],
  '/api/secrets': ['GMAIL_APP_PASSWORD', 'SMTP_PASSWORD'],
  '/api/costs': { total_usd: 0, paid_cap_usd: 0, local_share: 0.82, by_route: [], by_model: [{ model: 'qwen3:0.6b', runs: 31, steps: 120, tokens_in: 152000, tokens_out: 29000, cost_usd: 0 }, { model: 'gpt-6-luna (free)', runs: 4, steps: 9, tokens_in: 40000, tokens_out: 6000, cost_usd: 0 }] },
  '/api/system/settings': { mode: 'standard', local_model: 'qwen3:0.6b', max_parallel_runs: 4, ask_route: 'codex', ask_engine: 'codex', ask_route_reason: 'Codex is ready' },
  '/api/assistant/settings': { engine: 'openai', active_engine: 'openai', route_reason: 'OpenAI-compatible API is ready', fallback_reason_code: 'ready', remember_previous_chats: true,
    openai_base_url: 'https://api.openai.com/v1', openai_model: 'gpt-4.1-mini', openai_secret_name: 'OPENAI_API_KEY',
    openai_monthly_cap_usd: 20, openai_input_usd_per_million: 0.4, openai_output_usd_per_million: 1.6, openai_spend_usd: 2.43,
    anthropic_model: '', anthropic_secret_name: '', anthropic_monthly_cap_usd: '', anthropic_input_usd_per_million: '', anthropic_output_usd_per_million: '', anthropic_spend_usd: 0, local_model: 'qwen3:0.6b',
    engines: [{ id: 'codex', label: 'Codex', available: true, reason: 'ready', reason_code: 'ready' },
      { id: 'claude', label: 'Claude', available: false, reason: 'not signed in', reason_code: 'sign_in' },
      { id: 'gemini', label: 'Gemini', available: false, reason: 'not signed in', reason_code: 'sign_in' },
      { id: 'local', label: 'Ollama', available: true, reason: 'ready', reason_code: 'ready' },
      { id: 'openai', label: 'OpenAI-compatible API', available: true, reason: 'ready', reason_code: 'ready' },
      { id: 'anthropic', label: 'Anthropic API', available: false, reason: 'needs settings', reason_code: 'needs_settings' }] },
  '/api/memory/compat': { ok: true, notes_checked: 536, problems: [] },
  '/api/node-types': [
    { type: 'schedule', label: 'Schedule', description: 'Start on a timer', fields: [{ key: 'every', label: 'Every', placeholder: 'daily 9am', default: '' }], branches: null },
    { type: 'command', label: 'Command', description: 'Run a command', fields: [{ key: 'command', label: 'Command', placeholder: 'echo hi', default: '' }], branches: null },
    { type: 'check', label: 'Check', description: 'Verify', fields: [{ key: 'command', label: 'Check command', placeholder: '', default: '' }], branches: ['yes', 'no'] },
    { type: 'approval', label: 'Approval', description: 'Ask the owner', fields: [{ key: 'prompt', label: 'Question', placeholder: '', default: '', multiline: true }], branches: ['yes', 'no'] },
    { type: 'note', label: 'Note', description: 'Write to memory', fields: [{ key: 'path', label: 'Note', placeholder: '', default: '' }], branches: null }],
  '/api/environments/website-monitor': { id: 'website-monitor', name: 'website monitor', nodes: [
    { id: 'n1', type: 'schedule', config: { every: 'every 6h' }, position: { x: 80, y: 40 } },
    { id: 'n2', type: 'command', config: { command: 'fetch https://example.org' }, position: { x: 80, y: 170 } },
    { id: 'n3', type: 'check', config: { command: 'changes detected' }, position: { x: 80, y: 300 } },
    { id: 'n4', type: 'note', config: { path: 'monitor/changes.md' }, position: { x: 360, y: 300 } }],
    edges: [{ id: 'e1', source: 'n1', target: 'n2', label: '' }, { id: 'e2', source: 'n2', target: 'n3', label: '' }, { id: 'e3', source: 'n3', target: 'n4', label: 'yes' }] },
}
const srv = http.createServer((q, r) => {
  let p = path.join(dist, decodeURIComponent(q.url.split('?')[0]))
  if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) p = path.join(dist, 'index.html')
  const ext = path.extname(p)
  r.writeHead(200, { 'Content-Type': { '.js': 'text/javascript', '.css': 'text/css', '.woff2': 'font/woff2', '.html': 'text/html' }[ext] || 'application/octet-stream' })
  fs.createReadStream(p).pipe(r)
}).listen(0)
const port = srv.address().port
const b = await chromium.launch(fs.existsSync('/opt/pw-browsers/chromium') ? { executablePath: '/opt/pw-browsers/chromium' } : {})
const pg = await b.newPage({ viewport: { width: Number(process.env.W || 1280), height: Number(process.env.H || 800) } })
pg.on('pageerror', e => console.log('PAGEERROR', String(e)))
await pg.route('**/templates/previews/*.png', route => {
  const name = path.basename(new URL(route.request().url()).pathname)
  const file = path.resolve('../../templates/previews', name)
  route.fulfill({ status: fs.existsSync(file) ? 200 : 404, contentType: 'image/png', body: fs.existsSync(file) ? fs.readFileSync(file) : Buffer.alloc(0) })
})
await pg.route('**/api/**', route => {
  const u = new URL(route.request().url())
  const key = Object.keys(F).find(k => u.pathname === k) ?? (u.pathname.startsWith('/api/runs/') && u.pathname.endsWith('/changes') ? '/api/runs/r3/changes' : u.pathname.startsWith('/api/runs/') ? '/api/runs/r3' : u.pathname.startsWith('/api/runs') ? '/api/runs' : null)
  route.fulfill({ status: key ? 200 : 404, contentType: 'application/json', body: JSON.stringify(key ? F[key] : { detail: 'not found' }) })
})
for (const hs of hashes) {
  await pg.goto(`http://localhost:${port}/#/${hs}`)
  await pg.waitForTimeout(900)
  const f = `${out}-${hs.replace(/\W+/g, '_') || 'home'}.png`
  await pg.screenshot({ path: f })
  console.log('shot', f)
}
await b.close(); srv.close()
