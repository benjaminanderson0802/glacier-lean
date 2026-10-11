// Independent painted-room layout check.
// Run after `npm run build`: node e2e/room_visual_acceptance.spec.mjs
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const root = path.resolve(web, '../..')
const evidence = path.join(root, 'docs/ui/evidence/C-ROOM-VISUAL-TESTER')
const { mockPort, uiPort, api, ui } = await e2ePorts()
const env = { ...process.env, GLACIER_API: api }
const processes = []
const start = (command, args) => {
  const child = spawn(command, args, { cwd: web, env, detached: true, stdio: 'ignore' })
  processes.push(child)
  return child
}
const stop = () => { for (const child of processes.reverse()) { try { process.kill(-child.pid, 'SIGTERM') } catch { /* already stopped */ } } }
process.on('exit', stop)

async function waitFor(url) {
  for (let i = 0; i < 150; i++) {
    try { if ((await fetch(url)).ok) return } catch { /* server is starting */ }
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  throw new Error(`startup timed out: ${url}`)
}

let browser
try {
  assert.ok(existsSync(path.join(web, 'dist/index.html')), 'run `npm run build` first')
  mkdirSync(evidence, { recursive: true })
  start('node', ['mock/mock_server.mjs', String(mockPort)])
  await waitFor(`${api}/api/ventures`)
  start('node', ['node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1', '--port', String(uiPort), '--strictPort'])
  await waitFor(ui)
  const executablePath = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(executablePath ? { executablePath } : {})

  const findings = []
  for (const [width, height] of [[1280, 800], [1440, 900]]) {
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 })
    const pageErrors = []
    page.on('pageerror', error => pageErrors.push(String(error)))
    await page.goto(ui, { waitUntil: 'domcontentloaded' })
    await page.getByTestId('splash').waitFor({ state: 'visible' })
    await page.screenshot({ path: path.join(evidence, `first-run-${width}x${height}.png`) })
    await page.getByTestId('splash-home').click()
    await page.getByTestId('screen-home').waitFor({ state: 'visible' })

    const verifyRoom = async label => {
      const room = await page.evaluate(() => {
        const stage = document.querySelector('.l-stage')
        const rect = element => {
          const box = element.getBoundingClientRect()
          return { x: Math.round(box.x), y: Math.round(box.y), width: Math.round(box.width), height: Math.round(box.height) }
        }
        const panels = ['.l-left', '.l-center', '.l-right'].map(selector => {
          const element = document.querySelector(selector)
          return { selector, box: rect(element), backdropFilter: getComputedStyle(element).backdropFilter }
        })
        const stageStyle = getComputedStyle(stage)
        const chrome = [...document.querySelectorAll('.l-stage .g-menu-item, .l-stage .l-side-head, .l-stage .g-panel-title, .l-stage .g-title')]
          .map(element => ({ text: (element.innerText || '').trim().slice(0, 80), textTransform: getComputedStyle(element).textTransform }))
        const hitTargets = [...document.querySelectorAll('.l-stage button, .l-stage a, .l-stage [role="button"], .l-stage [role="tab"], .l-stage input, .l-stage select, .l-stage textarea')]
          .filter(element => {
            const style = getComputedStyle(element)
            const box = element.getBoundingClientRect()
            return style.display !== 'none' && style.visibility !== 'hidden' && box.width > 0 && box.height > 0
          }).map(element => {
            const box = element.getBoundingClientRect()
            const x = box.left + box.width / 2
            const y = box.top + box.height / 2
            const top = document.elementFromPoint(x, y)
            return {
              label: (element.getAttribute('aria-label') || element.innerText || element.getAttribute('placeholder') || element.tagName).trim().replace(/\s+/g, ' ').slice(0, 70),
              testid: element.getAttribute('data-testid'),
              width: Math.round(box.width), height: Math.round(box.height),
              clippedByViewport: box.left < 0 || box.top < 0 || box.right > innerWidth || box.bottom > innerHeight,
              centerObscured: !!top && top !== element && !element.contains(top),
              tooSmall: box.width < 24 || box.height < 24,
            }
          })
        return {
          viewport: { width: innerWidth, height: innerHeight },
          roomImage: stageStyle.backgroundImage,
          roomImageSize: stageStyle.backgroundSize,
          stage: rect(stage),
          fontFamily: getComputedStyle(document.body).fontFamily,
          nunitoLoaded: document.fonts.check('14px Nunito'),
          panels,
          chrome,
          horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
          hitTargetIssues: hitTargets.filter(item => item.clippedByViewport || item.centerObscured || item.tooSmall),
        }
      })

      assert.match(room.roomImage, /limbo\/room\.webp/, `${label}: exact painted room asset is the stage background`)
      assert.equal(room.panels.length, 3, `${label}: left, center, and right frosted panels exist`)
      for (const panel of room.panels) {
        assert.ok(panel.box.width > 0 && panel.box.height > 0, `${label}: ${panel.selector} has visible area`)
        assert.notEqual(panel.backdropFilter, 'none', `${label}: ${panel.selector} uses a frosted backdrop`)
      }
      assert.match(room.fontFamily, /Nunito/iu, `${label}: screen uses Nunito`)
      assert.ok(room.nunitoLoaded, `${label}: bundled Nunito face is loaded`)
      assert.ok(room.chrome.length > 0 && room.chrome.every(item => item.textTransform === 'lowercase'), `${label}: room chrome uses lowercase rendering`)
      assert.equal(room.horizontalOverflow, false, `${label}: no page-level horizontal overflow`)
      findings.push({ screen: label, ...room })
      await page.screenshot({ path: path.join(evidence, `${label}-${width}x${height}.png`), fullPage: false })
    }

    await verifyRoom('home')
    await page.getByTestId('nav-automations').click()
    await page.getByTestId('screen-automations').waitFor({ state: 'visible' })
    await verifyRoom('automations')
    await page.getByTestId('filter-ventures').click()
    await page.getByTestId('venture-list').waitFor({ state: 'visible' })
    await verifyRoom('ventures')
    assert.deepEqual(pageErrors, [], `${width}x${height}: no uncaught page errors`)
    await page.close()
  }
  writeFileSync(path.join(evidence, 'layout-findings.json'), `${JSON.stringify(findings, null, 2)}\n`)
  console.log(`PASS C-ROOM-VISUAL-TESTER: first-run + home, automations, ventures at both viewports; visual reports saved to ${path.relative(root, evidence)}`)
} finally {
  await browser?.close()
  stop()
}
