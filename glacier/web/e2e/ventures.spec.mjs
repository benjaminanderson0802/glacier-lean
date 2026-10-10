// Acceptance checks for the venture cards and the pinned Your steps inbox.
// Run after `npm run build`: node e2e/ventures.spec.mjs
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const { mockPort, uiPort, api, ui } = await e2ePorts()
const children = []
const start = (command, args, extraEnv = {}) => {
  const child = spawn(command, args, { cwd: root, env: { ...process.env, ...extraEnv }, stdio: 'ignore', detached: true })
  children.push(child); return child
}
const cleanup = () => { for (const child of children.reverse()) { try { process.kill(-child.pid, 'SIGTERM') } catch {} } }
process.on('exit', cleanup)
const waitHttp = async url => { for (let index = 0; index < 100; index++) { try { if ((await fetch(url)).status < 500) return } catch {} await new Promise(resolve => setTimeout(resolve, 200)) } throw new Error(`timeout: ${url}`) }
const check = (condition, message) => { console.log(`[ventures] ${condition ? 'ok  ' : 'FAIL'} ${message}`); if (!condition) throw new Error(message) }
let browser

try {
  if (!existsSync(path.join(root, 'dist/index.html'))) throw new Error('dist/ missing - run `npm run build` first')
  start('node', ['mock/mock_server.mjs', String(mockPort)])
  await waitHttp(`http://localhost:${mockPort}/api/ventures`)
  start('npx', ['vite', 'preview', '--port', String(uiPort), '--strictPort'], { GLACIER_API: api })
  await waitHttp(ui)
  browser = await chromium.launch((p => p ? { executablePath: p } : {})(process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : '')))
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  await context.addInitScript(() => { window.__GLACIER_TOKEN__ = 'mock-venture-token-not-rendered' })
  const page = await context.newPage()
  await page.goto(`${ui}/#/home`, { waitUntil: 'networkidle' })
  check(await page.getByTestId('needs-you').getByText('connect the fleet account').isVisible(), 'setup steps appear in Home needs you')
  check(await page.getByTestId('health-report').getByTestId('venture-daily-digest').isVisible(), 'Home shows one daily digest across installed ventures')
  check(await page.getByTestId('needs-you').getByText('Your step: review the dispatch list').isVisible(), 'approval steps appear in Home needs you')
  const messenger = page.getByTestId('messenger')
  await messenger.getByTestId('messenger-your-steps').click()
  await messenger.getByText('Your step: review the dispatch list').waitFor({ state: 'visible' })
  check(await messenger.getByTestId('venture-secret-FLEET_KEY').isVisible(), 'the pinned Glacier inbox shows the inline secret field')
  check(await messenger.getByTestId('venture-secret-FLEET_REGION').isVisible(), 'the same inbox step requests every connection key together')
  check(await messenger.getByRole('link', { name: /fleet\.example\.test/ }).getAttribute('target') === '_blank', 'setup links open in a browser tab')
  await messenger.getByTestId('venture-step-done-run-dispatch-waiting').click()
  await messenger.getByText('Your step: review the dispatch list').waitFor({ state: 'detached' })
  check(true, 'Done approves and removes a waiting Your step')
  await messenger.getByTestId('messenger-steps-back').click()

  await page.getByTestId('nav-automations').click()
  await page.getByTestId('filter-ventures').click()
  const card = page.getByTestId('venture-truck-dispatch')
  await card.waitFor({ state: 'visible' })
  check(await card.getByTestId('venture-status-truck-dispatch').textContent() === 'setting up', 'venture status is shown')
  check(await card.getByText(/4 runs/).isVisible(), 'today counts are shown')
  check(await card.getByText(/next run/i).isVisible(), 'the next scheduled run is shown')

  await card.getByTestId('venture-run-truck-dispatch').click()
  await page.waitForURL(/automations\/flow\/dispatch-preview\/run-/)
  await page.getByTestId('run-steps').waitFor({ state: 'visible' })
  check(page.url().includes('/dispatch-preview/'), 'run now starts the manifest dry-run flow')
  await page.getByTestId('nav-automations').click()
  await page.getByTestId('filter-ventures').click()
  const refreshed = page.getByTestId('venture-truck-dispatch')
  await refreshed.getByTestId('venture-toggle-truck-dispatch').click()
  await page.getByTestId('venture-status-truck-dispatch').getByText('paused').waitFor()
  await refreshed.getByTestId('venture-toggle-truck-dispatch').click()
  await page.getByTestId('venture-status-truck-dispatch').getByText('running').waitFor()
  check(true, 'pause and resume update the venture status')

  await refreshed.getByTestId('venture-secret-FLEET_KEY').fill('mock-fleet-token-123')
  await refreshed.getByTestId('venture-secret-FLEET_REGION').fill('mock-region-token-456')
  await refreshed.getByTestId('venture-step-done-fleet-key').click()
  await refreshed.getByTestId('venture-secret-FLEET_KEY').waitFor({ state: 'detached' })
  const secrets = await (await fetch(`${api}/api/secrets`)).json()
  check(secrets.includes('FLEET_KEY') && secrets.includes('FLEET_REGION'), 'Done stores every key by name and clears the setup step')

  await page.getByTestId('nav-home').click()
  check(await page.getByTestId('needs-you').getByText('connect the fleet account').count() === 0, 'completed setup items clear from Home needs you')
  check(!(await page.locator('body').innerText()).includes('mock-fleet-token-123') && !(await page.locator('body').innerText()).includes('mock-region-token-456'), 'key values are never shown again')
  await page.close()
} catch (error) {
  console.error('[ventures] ERROR', error)
  process.exitCode = 1
} finally {
  await browser?.close()
  cleanup()
}
if (!process.exitCode) console.log('PASS')
