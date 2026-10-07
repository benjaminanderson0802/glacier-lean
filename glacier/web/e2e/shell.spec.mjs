// Shell test: exactly five top-level options, each screen renders on-theme, keyboard shortcuts work.
// Run after `npx vite build` (check:ui does this). Uses the same mock backend as core.spec.mjs.
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const MOCK_PORT = 8788, UI_PORT = 4318, UI = `http://localhost:${UI_PORT}`
const procs = []
const start = (cmd, args, env = {}) => { const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true }); procs.push(p); return p }
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch { /* gone */ } } procs.length = 0 }
process.on('exit', cleanup)
const waitHttp = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch { /* not up */ } await new Promise(r => setTimeout(r, 200)) } throw new Error(`timeout ${url}`) }
let failures = 0
const check = (c, label) => { console.log(`[shell] ${c ? 'ok  ' : 'FAIL'} ${label}`); if (!c) failures++ }

let browser
try {
  start('node', ['mock/mock_server.mjs', String(MOCK_PORT)])
  await waitHttp(`http://localhost:${MOCK_PORT}/api/environments`)
  start('npx', ['vite', 'preview', '--port', String(UI_PORT), '--strictPort'], { GLACIER_API: `http://localhost:${MOCK_PORT}` })
  await waitHttp(UI)
  const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(exe ? { executablePath: exe } : {})
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
  const errors = []
  page.on('pageerror', e => errors.push(String(e)))
  await page.goto(UI, { waitUntil: 'networkidle' })

  const tabs = await page.locator('[role=tablist] [role=tab]').allTextContents()
  check(tabs.length === 5 && tabs.join(',') === 'Home,Ask,Automations,Memory,Settings', `exactly five options (got ${tabs.join(',')})`)
  for (const t of ['home', 'ask', 'automations', 'memory', 'settings']) {
    await page.getByTestId(`nav-${t}`).click()
    await page.getByTestId(`screen-${t}`).waitFor()
    const active = await page.getByTestId(`nav-${t}`).getAttribute('aria-selected')
    const font = await page.getByTestId('page-title').evaluate(el => getComputedStyle(el).fontFamily)
    check(active === 'true' && /Glacier Head/.test(font), `${t}: opens, tab active, title in the pixel font`)
  }
  const bodyFont = await page.evaluate(() => getComputedStyle(document.body).fontFamily)
  check(/Glacier Body/.test(bodyFont), 'body text uses the pixel body font')
  const fontsOk = await page.evaluate(async () => { await document.fonts.ready; return document.fonts.check('20px "Glacier Body"') && document.fonts.check('20px "Glacier Head"') })
  check(fontsOk, 'bundled pixel fonts loaded (offline)')

  await page.getByTestId('nav-automations').click()
  await page.getByTestId('flow-new').click()
  await page.getByTestId('flow-new-name').fill('Shell test')
  await page.getByTestId('flow-new-create').click()
  await page.getByTestId('env-name').waitFor()
  check(await page.getByTestId('env-name').inputValue() === 'Shell test', 'New opens the builder with the flow named')
  await page.getByTestId('save').click()
  await page.waitForFunction(() => document.querySelector('[data-testid=last-commit]')?.textContent !== '-')
  await page.getByTestId('nav-automations').click()
  await page.getByTestId('flow-shell-test').waitFor()
  check(true, 'saved flow appears in the Automations list')
  await page.getByTestId('flow-shell-test').click()
  await page.getByTestId('env-name').waitFor()
  check(await page.getByTestId('env-name').inputValue() === 'Shell test', 'clicking a flow opens it in the builder')

  await page.keyboard.press('Control+k')
  await page.getByTestId('command-palette').waitFor()
  await page.getByTestId('command-input').fill('memory')
  await page.keyboard.press('Enter')
  await page.getByTestId('screen-memory').waitFor()
  check(true, 'Ctrl+K palette jumps to Memory')
  await page.keyboard.press('Control+Tab')
  await page.getByTestId('screen-settings').waitFor()
  check(true, 'Ctrl+Tab moves to the next option')

  check(errors.length === 0, `no page errors${errors.length ? ': ' + errors.join(' | ') : ''}`)
} catch (e) { console.error(e); failures++ } finally { await browser?.close(); cleanup() }
console.log(failures ? `FAIL (${failures})` : 'PASS')
process.exit(failures ? 1 : 0)
