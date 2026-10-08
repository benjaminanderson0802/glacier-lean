// Desktop controls must call Tauri's window bridge; browser builds must hide them.
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const { mockPort: MOCK_PORT, uiPort: UI_PORT, api: API, ui: UI } = await e2ePorts()
const procs = []
const start = (cmd, args, env = {}) => { const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true }); procs.push(p); return p }
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch { /* gone */ } } procs.length = 0 }
process.on('exit', cleanup)
const waitHttp = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch { /* not up */ } await new Promise(r => setTimeout(r, 200)) } throw new Error(`timeout ${url}`) }
let failures = 0
const check = (ok, label) => { console.log(`[window-controls] ${ok ? 'ok  ' : 'FAIL'} ${label}`); if (!ok) failures++ }
let browser
try {
  start('node', ['mock/mock_server.mjs', String(MOCK_PORT)])
  await waitHttp(`http://localhost:${MOCK_PORT}/api/environments`)
  start('npx', ['vite', 'preview', '--port', String(UI_PORT), '--strictPort'], { GLACIER_API: API })
  await waitHttp(UI)
  const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(exe ? { executablePath: exe } : {})
  const page = await browser.newPage()
  await page.goto(UI, { waitUntil: 'networkidle' })
  check(await page.locator('.g-winctl').count() === 0, 'browser build has no window controls')

  const desktopPage = await browser.newPage()
  const windowCommands = []
  await desktopPage.exposeFunction('__recordWindowCommand', command => windowCommands.push(command))
  await desktopPage.addInitScript(() => {
    window.__windowCommands = []
    window.__TAURI_INTERNALS__ = {
      metadata: { currentWindow: { label: 'main' } },
      invoke: async (command, args) => { window.__windowCommands.push(command); void window.__recordWindowCommand(command); return undefined },
    }
  })
  await desktopPage.goto(UI, { waitUntil: 'networkidle' })
  // The startup splash covers the entire window until the user dismisses it.
  await desktopPage.getByTestId('splash').waitFor()
  await desktopPage.keyboard.press('Escape')
  const minimize = desktopPage.getByRole('button', { name: 'Minimise' })
  const close = desktopPage.getByRole('button', { name: 'Close' })
  check(await minimize.count() === 1 && await close.count() === 1, 'desktop build shows minimise and close controls')
  await minimize.click()
  await desktopPage.waitForFunction(() => window.__windowCommands.includes('plugin:window|minimize'))
  check(await desktopPage.evaluate(() => window.__windowCommands.includes('plugin:window|minimize')), 'minimise calls the Tauri window bridge')
  await close.click()
  await desktopPage.waitForFunction(() => window.__windowCommands.includes('plugin:window|close'))
  check(await desktopPage.evaluate(() => window.__windowCommands.includes('plugin:window|close')), 'close calls the Tauri window bridge')
} catch (e) { console.error(e); failures++ } finally { await browser?.close(); cleanup() }
if (failures) process.exitCode = 1
