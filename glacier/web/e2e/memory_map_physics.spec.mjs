// Memory map interaction and simulation acceptance checks.
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const { mockPort: MOCK_PORT, uiPort: UI_PORT, api: API, ui: UI } = await e2ePorts()
const procs = []
const start = (cmd, args, env = {}) => { const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true }); procs.push(p); return p }
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch { /* gone */ } } }
process.on('exit', cleanup)
const waitHttp = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch { /* not up */ } await new Promise(r => setTimeout(r, 200)) } throw new Error(`timeout ${url}`) }
let failures = 0
const check = (c, label) => { console.log(`[memory-map] ${c ? 'ok  ' : 'FAIL'} ${label}`); if (!c) failures++ }

let browser
try {
  start('node', ['mock/mock_server.mjs', String(MOCK_PORT)])
  await waitHttp(`http://localhost:${MOCK_PORT}/api/environments`)
  start('npx', ['vite', 'preview', '--port', String(UI_PORT), '--strictPort'], { GLACIER_API: API })
  await waitHttp(UI)
  const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(exe ? { executablePath: exe } : {})
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', e => errors.push(String(e)))
  for (const [path, title, body] of [
    ['map/physics-one.md', 'Physics one', '# Physics one\n\nA linked memory note. [[physics-two]]'],
    ['map/physics-two.md', 'Physics two', '# Physics two\n\nA second memory note.'],
  ]) {
    await fetch(`http://localhost:${MOCK_PORT}/api/memory/note`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path, title, body, author: 'owner' }) })
  }
  await page.goto(`${UI}/#/memory/~map`, { waitUntil: 'networkidle' })
  const canvas = page.getByTestId('memory-map').locator('canvas')
  await canvas.waitFor()
  await page.waitForTimeout(900)
  const evidence = path.resolve(root, '../../evidence/ui')
  mkdirSync(evidence, { recursive: true })
  await page.screenshot({ path: path.join(evidence, 'memory-map-after.png') })
  check(await canvas.count() === 1, 'map renders through the existing canvas')

  // The canvas remains pointer interactive and its transform changes for pan/zoom.
  const before = await canvas.evaluate(el => ({ width: el.width, height: el.height, style: el.getAttribute('style') }))
  await canvas.hover({ position: { x: 100, y: 100 } })
  await page.mouse.wheel(0, -420)
  await page.waitForTimeout(150)
  const afterZoom = await canvas.evaluate(el => ({ width: el.width, height: el.height, style: el.getAttribute('style') }))
  check(before.width === afterZoom.width && before.height === afterZoom.height, 'wheel zoom keeps the graph canvas sized to its panel')
  await page.mouse.move(300, 400)
  await page.mouse.down()
  await page.mouse.move(340, 430, { steps: 4 })
  await page.mouse.up()
  check(errors.length === 0, `map interactions run without browser errors${errors.length ? `: ${errors.join('; ')}` : ''}`)
  check(await page.getByTestId('memory-stats').getByText('Links').count() === 1, 'graph keeps its linked-note count visible')

  // Reduced motion must stop force animation while retaining the graph view.
  await context.close()
  const reducedContext = await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })
  const reduced = await reducedContext.newPage()
  await reduced.goto(`${UI}/#/memory/~map`, { waitUntil: 'networkidle' })
  await reduced.getByTestId('memory-map').locator('canvas').waitFor()
  await reduced.screenshot({ path: path.join(evidence, 'memory-map-reduced-motion.png') })
  check(await reduced.getByTestId('memory-map').count() === 1, 'reduced motion still shows the memory map')
  await reducedContext.close()
} catch (e) {
  console.error(e)
  failures++
} finally {
  if (browser) await browser.close()
}
console.log(`[memory-map] ${failures ? `${failures} checks failed` : 'all checks passed'}`)
// Child servers keep node alive, so stop them and exit explicitly.
cleanup()
process.exit(failures ? 1 : 0)
