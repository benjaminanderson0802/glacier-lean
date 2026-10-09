// Check that keyboard help navigation lands on the rendered Settings help panel.
// Run after `npm run build`: node e2e/settings_help.spec.mjs
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const port = 4336, ui = `http://localhost:${port}`
let preview, browser
const waitHttp = async () => { for (let i = 0; i < 100; i++) { try { if ((await fetch(ui)).ok) return } catch {} await new Promise(r => setTimeout(r, 100)) } throw new Error('preview did not start') }
try {
  if (!existsSync(path.join(root, 'dist/index.html'))) throw new Error('dist/ missing - run `npm run build` first')
  preview = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), 'preview', '--port', String(port), '--strictPort'], { cwd: root, stdio: 'ignore' })
  await waitHttp()
  const executablePath = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(executablePath ? { executablePath } : {})
  const page = await browser.newPage()
  await page.route('**/api/system/check', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
    cpu_cores: 4, memory_gb: 8, disk_free_gb: 20, ollama_models: [], tools: {},
    recommended: { mode: 'standard', local_model: 'none', max_parallel_runs: 1 }, messages: [],
  }) }))
  await page.goto(`${ui}/#/settings`, { waitUntil: 'networkidle' })
  await page.keyboard.press('F1')
  const help = page.locator('section[data-testid="settings-help"]')
  await help.waitFor()
  if (!(await help.getByText('F1', { exact: true }).count())) throw new Error('help keyboard shortcut content is missing')
  console.log('PASS: F1 opens the registered Settings help panel')
} finally {
  await browser?.close()
  preview?.kill('SIGTERM')
}
