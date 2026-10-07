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
  '/api/runs': [{ run_id: 'x', env_id: 'e', status: 'done', started_at: h(2) }],
  '/api/memory/notes': [{ path: 'ideas/products.md', title: 'Product ideas', author: 'assistant', updated: h(3), tags: ['projects'] }, { path: 'people/sam.md', title: 'Sam', author: 'you', updated: h(30), tags: ['people'] }, { path: 'prefs.md', title: 'Preferences', author: 'you', updated: h(80), tags: ['preferences'] }],
  '/api/memory/note': { path: 'ideas/products.md', body: '# Product ideas\n\n- pixel desk lamp\n- glacier mug\n\nSee [[people/sam]].', meta: { title: 'Product ideas' }, links_out: ['people/sam'], links_in: [] },
  '/api/memory/history': [{ commit: 'a1b2c3d4', author: 'assistant', date: h(3), message: 'added product ideas' }],
  '/api/system/check': { cpu_cores: 8, memory_gb: 16, disk_free_gb: 120, ollama_models: ['qwen3:0.6b'], tools: { codex: { found: true, version: '0.9' }, ollama: { found: true, version: '0.12' }, git: { found: true, version: '2.42.0' } }, recommended: { mode: 'standard', local_model: 'qwen3:0.6b', max_parallel_runs: 4 }, messages: [] },
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
await pg.route('**/api/**', route => {
  const u = new URL(route.request().url())
  const key = Object.keys(F).find(k => u.pathname === k) ?? (u.pathname.startsWith('/api/runs') ? '/api/runs' : null)
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
