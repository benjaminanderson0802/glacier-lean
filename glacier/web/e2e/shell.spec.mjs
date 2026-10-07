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
  await page.getByTestId('splash').waitFor()
  check(true, 'start screen shows on launch')
  await page.keyboard.press('Enter')
  await page.getByTestId('screen-home').waitFor()
  check(await page.getByTestId('splash').count() === 0, 'Enter on the start screen continues to Home')

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
  await page.getByTestId('run-steps').waitFor()
  check(await page.getByTestId('page-title').textContent() === 'Shell test', 'clicking a flow opens its Run view')
  await page.getByTestId('run-history').click()
  await page.getByTestId('past-runs').waitFor()
  check(true, 'Past runs view opens')
  await page.goBack()
  await page.getByTestId('open-builder').click()
  const named = await page.waitForFunction(() => document.querySelector('[data-testid=env-name]')?.value === 'Shell test', null, { timeout: 8000 }).then(() => true, () => false)
  check(named, 'Edit flow opens the builder')

  // friendly editor: new note, then a second note that links to it via [[ suggestions, then undo
  await page.getByTestId('nav-memory').click()
  await page.getByTestId('note-new').click()
  await page.getByTestId('note-title').fill('Shopping list')
  await page.getByTestId('note-body').fill('milk and eggs')
  await page.getByTestId('note-save').click()
  await page.getByTestId('note-saved').waitFor()
  check(/milk and eggs/.test(await page.getByTestId('memory-note-body').textContent()), 'new note saved and shown')
  await page.getByTestId('note-new').click()
  await page.getByTestId('note-title').fill('Weekend plan')
  await page.getByTestId('note-body').click()
  await page.keyboard.type('buy things from [[Shop')
  await page.getByTestId('link-suggest').waitFor()
  await page.keyboard.press('Enter')
  check((await page.getByTestId('note-body').inputValue()).includes('[[shopping-list]]'), 'typing [[ suggests notes and inserts a link')
  await page.getByTestId('note-save').click()
  await page.getByTestId('note-saved').waitFor()
  await page.getByText('Links to').waitFor()
  check(true, 'saved note shows its outgoing link')
  await page.getByTestId('note-edit').click()
  await page.getByTestId('note-body').fill('changed my mind')
  await page.getByTestId('note-save').click()
  await page.getByTestId('note-saved').waitFor()
  await page.getByTestId('note-undo').click()
  await page.waitForFunction(() => /\[\[shopping-list\]\]/.test(document.querySelector('[data-testid=memory-note-body]')?.textContent ?? ''))
  check(true, 'Undo restores the previous version')

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
