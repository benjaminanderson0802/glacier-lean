// Desktop controls must call Tauri's window bridge; browser builds must hide them.
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const MOCK_PORT = 8791, UI_PORT = 4321, UI = `http://localhost:${UI_PORT}`
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
  start('npx', ['vite', 'preview', '--port', String(UI_PORT), '--strictPort'], { GLACIER_API: `http://localhost:${MOCK_PORT}` })
  await waitHttp(UI)
  const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(exe ? { executablePath: exe } : {})
  const page = await browser.newPage()
  await page.goto(UI, { waitUntil: 'networkidle' })
  check(await page.locator('.g-winctl').count() === 0, 'browser build has no window controls')

  const desktopPage = await browser.newPage()
  await desktopPage.addInitScript(() => {
    window.__windowCommands = []
    window.__TAURI_INTERNALS__ = {
      metadata: { currentWindow: { label: 'main' } },
      invoke: async (command, args) => { window.__windowCommands.push({ command, args }); return undefined },
    }
  })
  await desktopPage.goto(UI, { waitUntil: 'networkidle' })
  const minimize = desktopPage.getByRole('button', { name: 'Minimise' })
  const close = desktopPage.getByRole('button', { name: 'Close' })
  check(await minimize.count() === 1 && await close.count() === 1, 'desktop build shows minimise and close controls')
  await minimize.click()
  await close.click()
  const commands = await desktopPage.evaluate(() => window.__windowCommands.map(x => x.command))
  check(commands.includes('plugin:window|minimize'), 'minimise calls the Tauri window bridge')
  check(commands.includes('plugin:window|close'), 'close calls the Tauri window bridge')
} catch (e) { console.error(e); failures++ } finally { await browser?.close(); cleanup() }
if (failures) process.exitCode = 1
