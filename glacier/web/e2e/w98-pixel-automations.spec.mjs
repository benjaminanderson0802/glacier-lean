// W98 visual contract for the pixel skinned Automations, template gallery, and flow editor.
import { chromium } from 'playwright'
import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
const dist = path.resolve('dist')
const server = http.createServer((req, res) => {
  let file = path.join(dist, decodeURIComponent(new URL(req.url, 'http://localhost').pathname))
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(dist, 'index.html')
  const ext = path.extname(file)
  res.writeHead(200, { 'Content-Type': ({ '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.woff2': 'font/woff2' })[ext] || 'text/html' })
  fs.createReadStream(file).pipe(res)
}).listen(0)
const port = server.address().port
const browser = await chromium.launch(fs.existsSync('/opt/pw-browsers/chromium') ? { executablePath: '/opt/pw-browsers/chromium' } : {})
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
const env = { id: 'weekly-report', name: 'Weekly report', enabled: true, nodes: [
  { id: 'n1', type: 'schedule', config: { cron: '0 9 * * 1' }, position: { x: 80, y: 40 } },
  { id: 'n2', type: 'command', config: { command: 'collect updates' }, position: { x: 80, y: 170 } },
  { id: 'n3', type: 'check', config: { command: 'verify report' }, position: { x: 80, y: 300 } },
], edges: [{ id: 'e1', source: 'n1', target: 'n2', label: '' }, { id: 'e2', source: 'n2', target: 'n3', label: '' }] }
const templates = [{ id: 'tpl-weekly-research', name: 'Weekly research', description: 'Research topics and save a checked report', author: 'Glacier', license: 'Apache-2.0', review_status: 'reviewed', installable: true, template: { ...env, nodes: env.nodes, edges: env.edges } }]
await page.route('**/api/**', route => {
  const url = new URL(route.request().url()), p = url.pathname
  let body = {}
  if (p === '/api/environments') body = [env]
  else if (p === '/api/environments/weekly-report') body = env
  else if (p === '/api/runs') body = []
  else if (p === '/api/teams') body = []
  else if (p === '/api/messages/threads') body = []
  else if (p === '/api/templates') body = templates
  else if (p === '/api/node-types') body = [
    { type: 'schedule', label: 'Schedule', description: 'Start on a timer', fields: [{ key: 'cron', label: 'Schedule', placeholder: '', default: '' }], branches: null },
    { type: 'command', label: 'Command', description: 'Run a command', fields: [{ key: 'command', label: 'Command', placeholder: '', default: '' }], branches: null },
    { type: 'check', label: 'Check', description: 'Verify a result', fields: [{ key: 'command', label: 'Check', placeholder: '', default: '' }], branches: ['yes', 'no'] },
  ]
  else if (p === '/api/system/settings') body = { mode: 'standard' }
  else if (p === '/api/secrets') body = []
  else if (p === '/api/memory/history') body = []
  else if (p === '/api/memory/notes') body = []
  else if (p === '/api/runs/weekly-report/changes') body = []
  route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
})
try {
  await page.goto(`http://localhost:${port}/#/automations`)
  await page.waitForTimeout(500)
  if (process.env.W98_CAPTURE === '1') await page.screenshot({ path: '../../evidence/ui/W98-automations.png', timeout: 60000 })
  await page.getByTestId('flow-templates').click()
  await page.getByTestId('tpl-tpl-weekly-research').waitFor()
  await page.getByTestId('tpl-tpl-weekly-research').click({ force: true })
  await page.getByTestId('template-detail').waitFor()
  await page.getByTestId('template-detail').locator('img').waitFor()
  const thumb = await page.getByTestId('tpl-tpl-weekly-research').locator('img').getAttribute('src')
  if (!thumb?.includes('/templates/previews/tpl-weekly-research.png')) throw new Error('template preview image is missing')
  if (!await page.getByText(/What you need:|Qué necesitas:/).count() || !await page.getByText(/What it makes:|Qué crea:/).count()) throw new Error('template Needs/Makes lines are missing')
  if (process.env.W98_CAPTURE === '1') await page.screenshot({ path: '../../evidence/ui/W98-template-gallery.png', timeout: 60000 })
  await page.goto(`http://localhost:${port}/#/automations/build/weekly-report`)
  await page.getByTestId('canvas').waitFor()
  await page.waitForFunction(() => document.querySelectorAll('[data-testid="node-n1"]').length > 0)
  if (!await page.locator('.react-flow__minimap').count()) throw new Error('canvas minimap is missing')
  if (!await page.locator('.react-flow__background').count()) throw new Error('canvas background is missing')
  if (process.env.W98_CAPTURE === '1') await page.screenshot({ path: '../../evidence/ui/W98-flow-editor.png', timeout: 60000 })
} finally { await browser.close(); server.close() }
console.log('W98 pixel automation screens ok')
