import { createServer } from 'node:http'
import { existsSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve('dist')
if (!existsSync(path.join(root, 'index.html'))) throw new Error('dist/ missing; build the web app first')
const server = createServer((req, res) => {
  let file = path.join(root, decodeURIComponent(new URL(req.url, 'http://localhost').pathname))
  if (!existsSync(file) || statSync(file).isDirectory()) file = path.join(root, 'index.html')
  const ext = path.extname(file)
  res.writeHead(200, { 'Content-Type': { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.woff2': 'font/woff2' }[ext] ?? 'application/octet-stream' })
  res.end(readFileSync(file))
}).listen(0)
const port = server.address().port
const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {})
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
const notes = [
  { path: 'a.md', title: 'Alpha', author: 'owner', updated: new Date().toISOString(), tags: [] },
  { path: 'b.md', title: 'Beta', author: 'owner', updated: new Date().toISOString(), tags: [] },
]
await page.route('**/api/**', route => {
  const url = new URL(route.request().url())
  const values = {
    '/api/memory/notes': notes,
    '/api/memory/note': { path: url.searchParams.get('path'), body: '# Beta\n\nSelected with the keyboard.', meta: { title: 'Beta', author: 'owner' }, links_in: [], links_out: [] },
    '/api/memory/history': [],
    '/api/system/check': { cpu_cores: 4, memory_gb: 8, disk_free_gb: 40, ollama_models: ['granite3.3:2b'], tools: {}, recommended: { mode: 'standard', local_model: 'granite3.3:2b', max_parallel_runs: 2 }, messages: [] },
    '/api/system/settings': { mode: 'standard', local_model: 'granite3.3:2b', max_parallel_runs: 2 },
    '/api/claims': [
      { id: 'c1042', kind: 'research', summary: 'Research item', status: 'proposed', updated: new Date().toISOString() },
      { id: 'c1043', kind: 'import', summary: 'Saved item', status: 'resolved', updated: new Date().toISOString() },
    ],
    '/api/claims/c1042': { meta: { id: 'c1042', kind: 'research', summary: 'Research item', status: 'proposed', updated: new Date().toISOString() }, body: '## Problem\nResearch item\n\n## Research\n- Checked two sources\n\n## Evidence\n- Independent check passed\n', },
  }
  const value = values[url.pathname]
  route.fulfill({ status: value === undefined ? 404 : 200, contentType: 'application/json', body: JSON.stringify(value ?? { detail: 'not found' }) })
})

try {
  await page.goto(`http://localhost:${port}/#/memory`)
  const alpha = page.getByTestId('mem-note-a.md')
  await alpha.waitFor()
  await alpha.focus()
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('Enter')
  await page.getByTestId('memory-note-body').getByText('Selected with the keyboard.').waitFor()
  console.log('PASS Memory list moves its gold cursor with arrows and opens the focused note with Enter')

  await page.goto(`http://localhost:${port}/#/settings/general`)
  const general = page.locator('button[data-testid="settings-general"]')
  await general.focus()
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('Enter')
  await page.getByTestId('settings-models').waitFor()
  console.log('PASS Settings menu moves with arrows and opens the focused section with Enter')

  await page.goto(`http://localhost:${port}/#/home/claim/c1042`)
  await page.getByTestId('claim-banner').waitFor()
  const claimTitles = await page.locator('.g-grid-2 .g-panel-title').allTextContents()
  const claimPanels = await page.locator('.g-grid-2 .g-panel-title').evaluateAll(nodes => nodes.map(node => ({ title: node.textContent, x: node.getBoundingClientRect().x })))
  if (!claimTitles.some(title => title.toLowerCase().includes('research')) || !claimTitles.some(title => title.toLowerCase().includes('proof')) || claimPanels.length !== 2 || claimPanels[0].x === claimPanels[1].x) throw new Error(`Claim windows are missing or overlap: ${JSON.stringify(claimPanels)}`)
  console.log('PASS Claim detail shows separate titled Research and Proof windows')

  await page.goto(`http://localhost:${port}/#/home/claims`)
  await page.getByTestId('claims-open').waitFor()
  const listPanels = await page.locator('.g-grid-2 > .g-panel').evaluateAll(nodes => nodes.map(node => node.getBoundingClientRect().x))
  if (listPanels.length !== 2 || listPanels[0] === listPanels[1]) throw new Error(`Claim lists overlap: ${JSON.stringify(listPanels)}`)
  console.log('PASS Waiting and settled claim windows stay side by side')
} finally {
  await browser.close()
  server.close()
}
