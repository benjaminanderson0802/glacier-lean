// U-FIX1: lowercase room chrome, preserve manifest text, and capture scroll proof at target sizes.
// Run after `npm run build`: node e2e/u-fix1.spec.mjs
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const root = path.resolve(web, '../..')
const evidence = path.join(root, 'docs/ui/evidence/U-FIX1')
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
  assert.ok(existsSync(path.join(web, 'dist/index.html')), 'build first')
  mkdirSync(evidence, { recursive: true })
  start('node', ['mock/mock_server.mjs', String(mockPort)])
  await waitFor(`${api}/api/ventures`)
  start('node', ['node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1', '--port', String(uiPort), '--strictPort'])
  await waitFor(ui)
  const executablePath = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(executablePath ? { executablePath } : {})

  for (const language of ['en', 'es']) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
    await page.addInitScript(lang => localStorage.setItem('glacier.language', lang), language)
    const errors = []
    page.on('pageerror', error => errors.push(String(error)))
    await page.route('**/api/ventures', async route => {
      const response = await route.fetch()
      const rows = await response.json()
      const source = rows[0]
      const expanded = Array.from({ length: 15 }, (_, index) => ({
        ...structuredClone(source),
        slug: `u-fix1-${index}`,
        name: index === 0 ? 'MixedCase Venture Name' : `Venture Project ${index + 1}`,
        description: index === 0 ? 'Keep This Description Exactly As Written.' : `Sample Manifest Description ${index + 1}.`,
        your_steps: index === 0 ? [{ id: 'mixed-step', title: 'Review The New Account', instructions: 'Paste API Key Without Changing Its Case.', done: false }] : [],
      }))
      await route.fulfill({ response, json: expanded })
    })
    await page.goto(`${ui}/#/automations/ventures`, { waitUntil: 'domcontentloaded' })
    await page.getByTestId('venture-u-fix1-14').waitFor()
    const live = page.getByTestId('room-live')
    await live.waitFor({ state: 'visible' })
    await page.getByTestId('room-running-count').waitFor()
    assert.equal(await page.locator('.l-overview summary').evaluateAll(elements => elements.map(element => getComputedStyle(element).textTransform).join(',')), 'lowercase,lowercase,lowercase')
    assert.equal((await page.getByTestId('room-running-count').innerText()).trim(), '2', 'right wall running count comes from engine home data')
    assert.ok(Number((await page.getByTestId('room-needs-count').innerText()).trim()) > 0, 'right wall needs-you count comes from engine home data')
    assert.equal(await page.locator('.venture-card').count(), 15)
    assert.equal(await page.locator('.venture-card h2').first().innerText(), 'MixedCase Venture Name')
    assert.equal(await page.locator('.venture-card-copy p.venture-user-content').first().innerText(), 'Keep This Description Exactly As Written.')
    assert.equal(await page.locator('.venture-step-copy strong.venture-user-content').first().innerText(), 'Review The New Account')
    assert.equal(await page.locator('.venture-step-copy p.venture-user-content').first().innerText(), 'Paste API Key Without Changing Its Case.')

    const labels = language === 'en' ? ['all', 'running', 'needs you', 'failed'] : ['todas', 'en ejecución', 'te necesitan', 'fallidas']
    const ids = language === 'en' ? ['filter-All', 'filter-Running', 'filter-Needs you', 'filter-Failed'] : ['filter-Todas', 'filter-En ejecución', 'filter-Te necesitan', 'filter-Fallidas']
    for (let index = 0; index < ids.length; index++) {
      const chip = page.getByTestId(ids[index])
      assert.equal((await chip.innerText()).trim(), labels[index], `${language} filter has its localized label`)
      assert.equal(await chip.evaluate(element => getComputedStyle(element).textTransform), 'lowercase', `${language} filter renders lowercase`)
    }
    const placeholder = page.getByTestId('flow-search')
    assert.equal(await placeholder.getAttribute('placeholder'), language === 'en' ? 'Search flows…' : 'Buscar flujos…')
    assert.equal(await placeholder.evaluate(element => getComputedStyle(element, '::placeholder').textTransform), 'lowercase')

    for (const [width, height] of [[1280, 800], [1440, 900], [1920, 1080]]) {
      await page.setViewportSize({ width, height })
      const list = page.getByTestId('venture-list')
      await list.evaluate(element => { element.scrollTop = 0 })
      const base = `${language}-portfolio-${width}x${height}`
      await page.screenshot({ path: path.join(evidence, `${base}-top.png`) })
      const before = await list.evaluate(element => ({ top: element.scrollTop, height: element.clientHeight, full: element.scrollHeight }))
      assert.ok(before.full > before.height + 20, `${base}: venture cards exceed the frosted panel interior`)
      await list.evaluate(element => { element.scrollTop = element.scrollHeight })
      const after = await list.evaluate(element => ({ top: element.scrollTop, max: element.scrollHeight - element.clientHeight }))
      assert.ok(after.top >= after.max - 2 && after.top > before.top, `${base}: center content scrolls to its final cards inside the panel`)
      await page.screenshot({ path: path.join(evidence, `${base}-bottom.png`) })
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${base}: no window horizontal overflow`)
    }
    assert.deepEqual(errors, [])
    await page.close()
  }
  console.log('PASS U-FIX1: English and Spanish lowercase controls, manifest case preserved, center panel scrolls at 1280x800, 1440x900, and 1920x1080; screenshots saved')
} finally {
  await browser?.close()
  stop()
}
