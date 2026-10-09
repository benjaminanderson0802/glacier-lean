// Spanish layout regression test at the two supported review sizes.
// Run after `npx vite build`: node e2e/spanish.spec.mjs
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const evidence = path.resolve(root, '../../evidence/ui')
const { mockPort: MOCK_PORT, uiPort: UI_PORT, api: API, ui: UI } = await e2ePorts()
const procs = []
const start = (cmd, args, env = {}) => {
  const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true })
  procs.push(p)
  return p
}
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch { /* gone */ } } }
process.on('exit', cleanup)
const waitHttp = async url => {
  for (let i = 0; i < 100; i++) {
    try { if ((await fetch(url)).status < 500) return } catch { /* not up */ }
    await new Promise(r => setTimeout(r, 200))
  }
  throw new Error(`timeout ${url}`)
}
const check = (condition, label) => { console.log(`[spanish] ${condition ? 'ok  ' : 'FAIL'} ${label}`); if (!condition) failures++ }
const sizes = [{ width: 1280, height: 800 }, { width: 1024, height: 700 }]
let browser
let failures = 0

try {
  if (!existsSync(path.join(root, 'dist/index.html'))) throw new Error('dist/ missing - run `npx vite build` first')
  mkdirSync(evidence, { recursive: true })
  start('node', ['mock/mock_server.mjs', String(MOCK_PORT)])
  await waitHttp(`http://localhost:${MOCK_PORT}/api/environments`)
  start('npx', ['vite', 'preview', '--port', String(UI_PORT), '--strictPort'], { GLACIER_API: API })
  await waitHttp(UI)
  const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(exe ? { executablePath: exe } : {})

  for (const size of sizes) {
    const page = await browser.newPage({ viewport: size })
    await page.addInitScript(() => localStorage.setItem('glacier.language', 'es'))
    const suffix = `${size.width}x${size.height}`
    await page.goto(UI + '/#/home', { waitUntil: 'networkidle' })
    await page.getByTestId('screen-home').waitFor()

    // Check text for clipping and the three Limbo panels against the painted room. The blurred
    // backdrop intentionally bleeds past the viewport, and child text can sit inside parent padding.
    const checkTextFit = async label => {
      const result = await page.evaluate(() => {
        const stage = document.querySelector('.l-stage').getBoundingClientRect()
        const panels = ['[data-testid="game-menu"]', '.l-center', '[data-testid="side-status"]']
        const panelOverflow = panels.flatMap(selector => {
          const rect = document.querySelector(selector).getBoundingClientRect()
          return rect.left < stage.left - 1 || rect.right > stage.right + 1 || rect.top < stage.top - 1 || rect.bottom > stage.bottom + 1 ? [selector] : []
        })
        const ignored = new Set(['SCRIPT', 'STYLE', 'PATH', 'RECT', 'LINE', 'CIRCLE', 'POLYGON', 'POLYLINE', 'ELLIPSE'])
        const elements = [...document.querySelectorAll('body *')].filter(el => {
          if (ignored.has(el.tagName.toUpperCase()) || !el.getClientRects().length) return false
          if (el.matches('.l-backdrop')) return false
          return getComputedStyle(el).visibility !== 'hidden'
        })
        const textOverflow = elements.flatMap(el => {
          const style = getComputedStyle(el)
          const text = [...el.childNodes].some(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim())
          const accessibleEllipsis = style.textOverflow === 'ellipsis' && Boolean(el.getAttribute('title'))
          const horizontalClip = text && !accessibleEllipsis && el.scrollWidth > el.clientWidth + 1 && ['hidden', 'clip'].includes(style.overflowX)
          const verticalClip = text && el.scrollHeight > el.clientHeight + 1 && ['hidden', 'clip'].includes(style.overflowY)
          const rect = el.getBoundingClientRect()
          const outsideViewport = rect.left < -1 || rect.right > innerWidth + 1
          let outsideScrollContainer = false
          for (let ancestor = el.parentElement; ancestor; ancestor = ancestor.parentElement) {
            const ancestorStyle = getComputedStyle(ancestor)
            if (!/(auto|scroll|hidden|clip)/.test(ancestorStyle.overflowX)) continue
            const box = ancestor.getBoundingClientRect()
            if (rect.right > box.right + 1) outsideScrollContainer = true
          }
          return horizontalClip || verticalClip || outsideViewport || outsideScrollContainer
            ? [{ text: el.textContent.trim().replace(/\s+/g, ' ').slice(0, 30), tag: el.tagName, className: typeof el.className === 'string' ? el.className.slice(0, 40) : '', rect: [rect.left, rect.top, rect.right, rect.bottom].map(Math.round), width: innerWidth }]
            : []
        })
        return { panelOverflow, textOverflow }
      })
      check(result.panelOverflow.length === 0 && result.textOverflow.length === 0, `${suffix} ${label}: glass panels stay in the room and text fits (${result.panelOverflow.join(', ')} ${result.textOverflow.slice(0, 25).map(x => `${x.tag}.${x.className} ${x.rect.join(',')}: ${x.text}`).join(' | ')})`)
    }

    // Screenshot the fresh Home view with Get started, and then the same tab set after visiting each.
    await page.getByTestId('starter').waitFor()
    await page.screenshot({ path: path.join(evidence, `es-home-get-started-${suffix}.png`), fullPage: false, timeout: 120000 })
    await checkTextFit('Home with Get started')
    await page.getByTestId('starter-hide').click()
    await page.getByTestId('nav-settings').click()
    await page.locator('button[data-testid="settings-general"]').click()
    await page.locator('section[data-testid="settings-general"] select').selectOption('es')
    const spanishTabs = await Promise.all(['home', 'ask', 'automations', 'memory', 'settings'].map(id => page.getByTestId(`nav-${id}`).textContent()))
    const tabIds = await page.locator('[role=tablist] [role=tab]').evaluateAll(els => els.map(el => el.getAttribute('data-testid')))
    check(tabIds.join(',') === 'nav-home,nav-ask,nav-automations,nav-memory,nav-settings' && spanishTabs.map(x => x.trim()).join(',') === 'Inicio,Crear,Flujos,Memoria,Ajustes', `${suffix} exactly five Spanish menu options (${spanishTabs.join(',')})`)
    for (const tab of ['home', 'ask', 'automations', 'memory', 'settings']) {
      await page.getByTestId(`nav-${tab}`).click()
      await page.getByTestId(`screen-${tab}`).waitFor()
      await checkTextFit(tab)
      await page.screenshot({ path: path.join(evidence, `es-${tab}-${suffix}.png`), fullPage: false, timeout: 120000 })
    }

    // Main Settings sections, plus a completed Run view and a flow editor.
    await page.getByTestId('nav-settings').click()
    for (const section of ['general', 'models', 'secrets', 'usage', 'data', 'system', 'help', 'about']) {
      await page.locator(`button[data-testid="settings-${section}"]`).click()
      await page.waitForTimeout(120)
      await checkTextFit(`Settings ${section}`)
      await page.screenshot({ path: path.join(evidence, `es-settings-${section}-${suffix}.png`), fullPage: false, timeout: 120000 })
    }
    await page.getByTestId('nav-automations').click()
    await page.getByTestId('flow-new').click()
    await page.getByTestId('flow-new-name').fill('Flujo de prueba')
    await page.getByTestId('flow-new-create').click()
    await page.getByTestId('palette').waitFor()
    await checkTextFit('flow editor')
    await page.screenshot({ path: path.join(evidence, `es-flow-editor-${suffix}.png`), fullPage: false, timeout: 120000 })

    await fetch(`http://localhost:${MOCK_PORT}/api/environments/spanish-run-demo`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: 'spanish-run-demo', name: 'Prueba de ejecución', nodes: [{ id: 'n1', type: 'command', config: { cmd: 'echo listo' }, position: { x: 0, y: 0 } }], edges: [] }),
    })
    const { run_id } = await (await fetch(`http://localhost:${MOCK_PORT}/api/environments/spanish-run-demo/run`, { method: 'POST' })).json()
    await page.goto(UI + `/#/automations/flow/spanish-run-demo/${run_id}`)
    await page.getByTestId('run-steps').waitFor()
    await checkTextFit('run view')
    await page.screenshot({ path: path.join(evidence, `es-run-view-${suffix}.png`), fullPage: false, timeout: 120000 })
    await page.close()
  }
} catch (error) {
  failures++
  console.error('[spanish] ERROR', error)
} finally {
  await browser?.close()
  cleanup()
}
console.log(failures ? `FAIL (${failures} failing checks)` : 'PASS')
process.exit(failures ? 1 : 0)
