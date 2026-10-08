// Trigger settings acceptance check against the in-memory mock API.
import { spawn } from 'node:child_process'
import { mkdirSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const out = path.resolve(root, '../../evidence/ui')
mkdirSync(out, { recursive: true })
const { mockPort: MOCK, uiPort: UI_PORT, api: API, ui: UI } = await e2ePorts()
const procs = []
const start = (cmd, args, env = {}) => { const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true }); procs.push(p); return p }
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch {} } }
process.on('exit', cleanup)
const waitHttp = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch {} await new Promise(r => setTimeout(r, 200)) } throw Error(`timeout ${url}`) }
let failures = 0
const check = (ok, label) => { console.log(`[triggers] ${ok ? 'ok  ' : 'FAIL'} ${label}`); if (!ok) failures++ }
let browser
try {
  start('node', ['mock/mock_server.mjs', String(MOCK)])
  await waitHttp(`http://localhost:${MOCK}/api/environments`)
  start('npx', ['vite', 'preview', '--port', String(UI_PORT), '--strictPort'], { GLACIER_API: API })
  await waitHttp(UI)
  const base = `http://localhost:${MOCK}`
  await fetch(`${base}/api/environments/triggers-demo`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: 'triggers-demo', name: 'Folder watch', enabled: true, nodes: [{ id: 'work', type: 'command', config: { cmd: 'echo ready' }, position: { x: 80, y: 80 } }], edges: [] }) })
  const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(exe ? { executablePath: exe } : {})
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, permissions: ['clipboard-read', 'clipboard-write'] })
  await context.addInitScript(() => { window.__GLACIER_TOKEN__ = 'mock-install-token-never-render-this' })
  const page = await context.newPage()
  await page.goto(UI, { waitUntil: 'networkidle' }); await page.keyboard.press('Enter'); await page.getByTestId('nav-automations').click(); await page.getByTestId('trigger-triggers-demo').waitFor()
  await page.screenshot({ path: path.join(out, 'automations-list-before.png'), fullPage: true })
  check(await page.getByTestId('trigger-choice-triggers-demo').inputValue() === 'manual', 'flow starts by hand by default')
  await page.getByTestId('trigger-choice-triggers-demo').selectOption('schedule')
  await page.getByTestId('trigger-schedule-triggers-demo').waitFor()
  await page.getByTestId('trigger-schedule-triggers-demo').fill('0 8 * * *'); await page.getByTestId('trigger-schedule-triggers-demo').blur()
  await page.waitForFunction(async () => (await (await fetch('/api/environments/triggers-demo')).json()).nodes.some(n => n.type === 'schedule' && n.config.cron === '0 8 * * *'))
  check(true, 'schedule choice and time are saved')
  await page.getByTestId('trigger-choice-triggers-demo').selectOption('file')
  await page.getByTestId('trigger-folder-triggers-demo').fill('/tmp/incoming'); await page.getByTestId('trigger-folder-triggers-demo').blur()
  await page.getByTestId('trigger-pattern-triggers-demo').fill('*.pdf'); await page.getByTestId('trigger-pattern-triggers-demo').blur()
  await page.waitForFunction(async () => { const e = await (await fetch('/api/environments/triggers-demo')).json(); const n = e.nodes.find(n => n.type === 'file_trigger'); return n?.config.folder === '/tmp/incoming' && n.config.pattern === '*.pdf' })
  check(true, 'folder and file pattern are saved')
  await page.getByTestId('trigger-choice-triggers-demo').selectOption('webhook')
  await page.screenshot({ path: path.join(out, 'automations-starts-when.png'), fullPage: true })
  await page.getByTestId('copy-hook-triggers-demo').click()
  check((await page.evaluate(() => navigator.clipboard.readText())).includes('/api/hooks/triggers-demo'), 'web address copy button copies the local address')
  await page.getByTestId('copy-token-triggers-demo').click()
  check(await page.evaluate(() => navigator.clipboard.readText()) === 'mock-install-token-never-render-this', 'token copy button copies the install token')
  check(!(await page.locator('body').innerText()).includes('mock-install-token-never-render-this'), 'token value never appears on screen')
  await fetch(`${base}/api/environments/triggers-demo/run`, { method: 'POST' })
  await page.reload({ waitUntil: 'networkidle' }); await page.keyboard.press('Enter'); await page.getByTestId('nav-automations').click()
  await page.getByTestId('last-trigger-run-triggers-demo').waitFor()
  await page.getByTestId('last-trigger-run-triggers-demo').click()
  await page.getByTestId('run-steps').waitFor()
  check(page.url().includes('/automations/flow/triggers-demo/run-'), 'last start links to the run it created')
  await page.getByTestId('nav-automations').click()
  await page.getByTestId('trigger-enabled-triggers-demo').click()
  await page.waitForFunction(async () => (await (await fetch('/api/environments/triggers-demo')).json()).enabled === false)
  await page.getByTestId('trigger-disabled-triggers-demo').waitFor()
  check(/will not start/.test(await page.getByTestId('trigger-disabled-triggers-demo').textContent()), 'paused flow says it will not start')
  await page.screenshot({ path: path.join(out, 'automations-list-after.png'), fullPage: true })
  check((await page.locator('[role=tablist] [role=tab]').allTextContents()).length === 5, 'trigger settings stay inside the existing five tabs')
  await page.getByTestId('flow-triggers-demo').click()
  await page.getByTestId('run-steps').waitFor()
  check(true, 'opening a flow from Automations still shows its run steps')
} catch (e) { console.error(e); failures++ } finally { await browser?.close(); cleanup() }
console.log(failures ? `FAIL (${failures})` : 'PASS')
process.exit(failures ? 1 : 0)
