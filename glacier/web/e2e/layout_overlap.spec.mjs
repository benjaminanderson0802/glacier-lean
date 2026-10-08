// Confirms that the flow canvas retains pointer access after a run opens output.
// Run after `npx vite build`: node e2e/layout_overlap.spec.mjs
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const MOCK_PORT = 8793, UI_PORT = 4323, UI = `http://localhost:${UI_PORT}`
const procs = []
const start = (cmd, args, env = {}) => { const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true }); procs.push(p); return p }
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch { /* gone */ } } procs.length = 0 }
process.on('exit', cleanup)
const waitHttp = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch { /* not up yet */ } await new Promise(r => setTimeout(r, 200)) } throw new Error(`timeout ${url}`) }
let failures = 0
const check = (c, label) => { console.log(`[layout] ${c ? 'ok  ' : 'FAIL'} ${label}`); if (!c) failures++ }
let browser

try {
  if (!existsSync(path.join(root, 'dist/index.html'))) throw new Error('dist/ missing - run `npx vite build` first')
  start('node', ['mock/mock_server.mjs', String(MOCK_PORT)])
  await waitHttp(`http://localhost:${MOCK_PORT}/api/environments`)
  start('npx', ['vite', 'preview', '--port', String(UI_PORT), '--strictPort'], { GLACIER_API: `http://localhost:${MOCK_PORT}` })
  await waitHttp(UI)
  const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(exe ? { executablePath: exe } : {})

  for (const viewport of [{ width: 1280, height: 800 }, { width: 1024, height: 700 }]) {
    const page = await browser.newPage({ viewport })
    const tid = id => page.getByTestId(id)
    const waitState = (node, state) => page.waitForSelector(`[data-testid="node-${node}"][data-state="${state}"]`, { timeout: 10000 })
    const clickAtCenter = async id => {
      const target = tid(id)
      const hit = await target.evaluate(el => {
        const rect = el.getBoundingClientRect()
        return document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)?.closest('[data-testid]')?.getAttribute('data-testid')
      })
      if (hit !== id) throw new Error(`${viewport.width}px ${id} center is intercepted by ${hit}`)
      await target.click({ force: true })
    }
    await page.goto(UI + '/#/automations/build', { waitUntil: 'networkidle' })
    await page.waitForSelector('[data-testid="ws-status"][data-connected="true"]', { timeout: 10000 })
    await page.waitForTimeout(300)
    await tid('new-env').click({ force: true })
    await tid('new-env-name').fill(`Layout ${viewport.width}`)
    await tid('new-env-create').click({ force: true })
    const paletteCommand = tid('palette-command')
    await paletteCommand.evaluate(el => el.scrollIntoView({ block: 'nearest', inline: 'center' }))
    await page.waitForTimeout(100)
    const paletteHit = await paletteCommand.evaluate(el => {
      const rect = el.getBoundingClientRect()
      const point = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)
      const describe = selector => { const box = document.querySelector(selector)?.getBoundingClientRect(); return box && { x: box.x, y: box.y, width: box.width, height: box.height } }
      return { target: el.getAttribute('data-testid'), hit: point?.closest('[data-testid]')?.getAttribute('data-testid') ?? point?.tagName, button: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }, tabs: describe('.tabs'), palette: describe('.palette'), center: describe('.center'), canvas: describe('.canvas') }
    })
    if (paletteHit.hit !== 'palette-command') throw new Error(`${viewport.width}px palette pointer geometry: ${JSON.stringify(paletteHit)}`)
    await clickAtCenter('palette-command')
    await tid('field-cmd').fill('echo layout-ok')
    const fit = page.locator('.react-flow__controls-fitview')
    if (await fit.count()) { await fit.click(); await page.waitForTimeout(250) }
    await clickAtCenter('run')
    await waitState('n1', 'done')
    await tid('terminal-panel').waitFor({ state: 'visible', timeout: 5000 })
    await page.waitForFunction(() => document.querySelector('[data-testid="run-status"]')?.textContent === 'done', null, { timeout: 10000 })
    await fit.click()
    await page.waitForTimeout(150)

    const rows = await page.evaluate(() => {
      const canvas = document.querySelector('[data-testid="canvas"]')?.getBoundingClientRect()
      const terminal = document.querySelector('[data-testid="terminal-panel"]')?.getBoundingClientRect()
      return { canvasHeight: canvas?.height ?? 0, canvasBottom: canvas?.bottom ?? 0, terminalTop: terminal?.top ?? 0 }
    })
    check(rows.canvasHeight >= 200 && rows.canvasBottom <= rows.terminalTop, `${viewport.width}x${viewport.height}: canvas stays at least 200px tall above the terminal row (${JSON.stringify(rows)})`)

    const hits = await page.locator('[data-testid^="node-"]').evaluateAll(nodes => nodes.map(node => {
      const rect = node.getBoundingClientRect()
      const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)
      return { id: node.getAttribute('data-testid'), hit: hit?.closest('[data-testid^="node-"]')?.getAttribute('data-testid') ?? hit?.getAttribute('data-testid'), center: { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) } }
    }))
    check(hits.length > 0 && hits.every(item => item.id === item.hit), `${viewport.width}x${viewport.height}: after run, node centers hit their own nodes (${JSON.stringify(hits)})`)
    await page.close()
  }
} catch (e) {
  failures++
  console.error('[layout] ERROR', e)
} finally {
  await browser?.close()
  cleanup()
}
console.log(failures ? `FAIL (${failures} failing checks)` : 'PASS')
process.exit(failures ? 1 : 0)
