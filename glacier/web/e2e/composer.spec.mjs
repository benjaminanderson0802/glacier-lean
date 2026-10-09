// Acceptance checks for the standalone modern composer gallery.
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const procs = []
const start = (cmd, args, env = {}) => { const p = spawn(cmd, args, { cwd: new URL('..', import.meta.url).pathname, env: { ...process.env, ...env }, stdio: 'ignore', detached: true }); procs.push(p); return p }
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch {} } }
process.on('exit', cleanup)
const wait = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).ok) return } catch {} await new Promise(r => setTimeout(r, 100)) } throw Error(`timeout ${url}`) }
const { mockPort, uiPort, ui } = await e2ePorts()
let browser
const errors = []
try {
  start('node', ['mock/mock_server.mjs', String(mockPort)])
  await wait(`${ui.replace(/:\d+$/, `:${mockPort}`)}/api/teams`)
  start('npx', ['vite', '--host', '127.0.0.1', '--port', String(uiPort), '--strictPort'], { GLACIER_API: `http://localhost:${mockPort}` })
  await wait(ui)
  browser = await chromium.launch(existsSync(process.env.PLAYWRIGHT_BROWSERS_PATH + '/chromium-1243/chrome-linux64/chrome') ? { executablePath: process.env.PLAYWRIGHT_BROWSERS_PATH + '/chromium-1243/chrome-linux64/chrome' } : {})
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
  page.on('pageerror', e => errors.push(String(e)))
  await page.goto(`${ui}/src/ui/modern/composer/route-entry.html#/ui-gallery-composer`)
  await page.getByTestId('composer').waitFor()
  const composer = page.getByTestId('composer')
  await composer.waitFor()

  const box = page.locator('.dg-composer textarea')
  await box.fill('/')
  await page.getByRole('option', { name: /search memory/i }).waitFor()
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('Enter')
  if (!((await box.inputValue()).includes('/flow'))) throw Error('slash command selection did not insert')
  await box.fill('@')
  await page.getByRole('option', { name: /weekly research digest/i }).waitFor()
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('Enter')
  if (!((await box.inputValue()).includes('Research sources'))) throw Error('mention selection did not insert')

  await composer.getByRole('button', { name: /engine/i }).click()
  await page.getByRole('option', { name: /local/i }).click()
  if (!await composer.getByRole('button', { name: /local/i }).count()) throw Error('engine selection did not update')
  await composer.getByRole('button', { name: /mode/i }).click()
  await page.getByRole('option', { name: /build interview/i }).click()
  if (!await composer.getByRole('button', { name: /build interview/i }).count()) throw Error('mode selection did not update')

  await box.fill('A short note')
  await box.press('Shift+Enter')
  await box.pressSequentially('with a second line')
  
  if (!(await box.inputValue()).includes('\n')) throw Error('Shift+Enter did not add a line')
  const beforeEnter = page.locator('[data-testid="sent-message"]')
  await box.press('Enter')
  await beforeEnter.waitFor()
  if (!await beforeEnter.textContent().then(x => x.includes('A short note'))) throw Error('Enter did not send')
  if (!await composer.getByRole('button', { name: /stop/i }).isVisible()) throw Error('busy state did not show Stop')
  await composer.getByRole('button', { name: /stop/i }).click()
  if (!await composer.getByRole('button', { name: /send/i }).isVisible()) throw Error('Stop did not return composer to idle')

  const fileButton = composer.getByRole('button', { name: 'Attach files' })
  await fileButton.click()
  await page.locator('input[type=file]').setInputFiles({ name: 'sample.txt', mimeType: 'text/plain', buffer: Buffer.from('hello') })
  await page.getByText('sample.txt').waitFor()
  await composer.getByRole('button', { name: /remove sample.txt/i }).click()
  if (await page.getByText('sample.txt').count()) throw Error('attachment remove failed')
  await page.locator('input[type=file]').setInputFiles({ name: 'sample.txt', mimeType: 'text/plain', buffer: Buffer.from('hello') })
  await box.focus()
  await page.evaluate(() => {
    const file = new File(['pasted'], 'pasted.txt', { type: 'text/plain' })
    const dt = new DataTransfer(); dt.items.add(file)
    document.querySelector('[data-testid="composer"] textarea').dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true }))
  })
  await page.getByText('pasted.txt').waitFor()
  await composer.evaluate(el => {
    const dt = new DataTransfer(); dt.items.add(new File(['drop'], 'dropped.txt', { type: 'text/plain' }))
    el.dispatchEvent(new DragEvent('dragenter', { bubbles: true, dataTransfer: dt }));
    el.dispatchEvent(new DragEvent('drop', { bubbles: true, dataTransfer: dt }))
  })
  await page.getByText('dropped.txt').waitFor()
  await page.getByRole('button', { name: /remove pasted.txt/i }).click()
  await page.getByRole('button', { name: /remove dropped.txt/i }).click()
  await page.getByRole('button', { name: /remove sample.txt/i }).click()

  await box.fill('x'.repeat(5001))
  await page.getByTestId('composer-error').waitFor()
  await box.fill('ready')
  await box.press('Escape')
  await page.screenshot({ path: '../../../evidence/ui/W131-composer-1280x800.png', animations: 'disabled' })
  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.screenshot({ path: '../../../evidence/ui/W131-composer-1920x1080.png', animations: 'disabled' })
  if (errors.length) throw Error(`browser errors: ${errors.join('; ')}`)
  console.log('composer acceptance PASS')
} finally { await browser?.close(); cleanup() }
