// Standalone overlay gallery acceptance checks.
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const { uiPort } = await e2ePorts()
const url = `http://localhost:${uiPort}/ui-gallery-overlays.html`
let preview, browser
const check = (condition, label) => { console.log(`[palette] ${condition ? 'ok  ' : 'FAIL'} ${label}`); if (!condition) throw new Error(label) }
const waitHttp = async target => { for (let i = 0; i < 100; i++) { try { if ((await fetch(target)).status < 500) return } catch { /* starting */ } await new Promise(r => setTimeout(r, 200)) } throw new Error(`timeout ${target}`) }

try {
  if (!existsSync(path.join(root, 'dist/ui-gallery-overlays.html'))) throw new Error('gallery build is missing; run npm run build first')
  preview = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), 'preview', '--port', String(uiPort), '--strictPort'], { cwd: root, env: process.env, stdio: 'ignore' })
  await waitHttp(url)
  const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(exe ? { executablePath: exe } : {})
  for (const viewport of [{ width: 1280, height: 800 }, { width: 1920, height: 1080 }]) {
    const page = await browser.newPage({ viewport })
    const errors = []
    page.on('pageerror', error => errors.push(String(error)))
    await page.goto(url, { waitUntil: 'networkidle' })
    await page.getByTestId('overlay-gallery').waitFor()
    check(await page.getByTestId('gallery-command').count() === 1 && await page.getByTestId('gallery-notifications').count() === 1, `${viewport.width}px: gallery mounts all overlays`)
    await page.keyboard.press('Control+k')
    await page.getByRole('dialog', { name: 'Command palette' }).waitFor()
    await page.getByTestId('command-query').fill('automations')
    check(await page.getByTestId('command-result').count() > 0, `${viewport.width}px: palette filters actions by query`)
    await page.keyboard.press('ArrowDown')
    await page.keyboard.press('Enter')
    check(await page.getByTestId('gallery-feedback').textContent() === 'Opened Automations', 'keyboard selection runs a registered action')
    await page.keyboard.press('Escape')
    await page.keyboard.press('?')
    await page.getByRole('dialog', { name: 'Keyboard shortcuts' }).waitFor()
    check((await page.getByTestId('shortcut-list').textContent()).includes('Open command palette'), 'shortcut sheet lists registered shortcuts')
    await page.keyboard.press('Escape')
    await page.getByTestId('notifications-bell').click()
    await page.getByRole('dialog', { name: 'Notifications' }).waitFor()
    check(await page.getByTestId('notification-item').count() >= 3, 'notifications show finished runs, approvals and failures')
    await page.getByTestId('notification-item').first().click()
    check((await page.getByTestId('gallery-feedback').textContent()).includes('Opened'), 'notification click-through invokes its registered action')
    check(errors.length === 0, `${viewport.width}px: no browser errors`)
    await page.close()
  }
} catch (error) {
  console.error('[palette] ERROR', error)
  process.exitCode = 1
} finally {
  await browser?.close()
  preview?.kill('SIGTERM')
}
if (!process.exitCode) console.log('PASS')
