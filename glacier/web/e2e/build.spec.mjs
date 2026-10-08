// Build team acceptance: interview -> approved spec -> approved plan -> team approval -> evaluator completion.
import { spawn } from 'node:child_process'
import { mkdir } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repo = path.resolve(root, '../..')
const mockPort = 4389, uiPort = 4390, ui = `http://localhost:${uiPort}`
const procs = []
const start = (cmd, args, env = {}) => { const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true }); procs.push(p); return p }
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch {} } }
process.on('exit', cleanup)
const waitHttp = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch {} await new Promise(r => setTimeout(r, 150)) } throw Error(`timeout ${url}`) }
let browser, failures = 0
const check = (value, label) => { console.log(`[build] ${value ? 'ok  ' : 'FAIL'} ${label}`); if (!value) failures++ }
try {
  start('node', ['mock/mock_server.mjs', String(mockPort)])
  await waitHttp(`http://localhost:${mockPort}/api/teams`)
  start('npx', ['vite', 'preview', '--port', String(uiPort), '--strictPort'], { GLACIER_API: `http://localhost:${mockPort}` })
  await waitHttp(ui)
  const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(exe ? { executablePath: exe } : {})
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
  const errors = []; page.on('pageerror', e => errors.push(String(e)))
  await mkdir(path.join(repo, 'evidence/ui'), { recursive: true })
  await page.goto(`${ui}/#/build`, { waitUntil: 'networkidle' })
  if (await page.getByTestId('splash').count()) await page.keyboard.press('Enter')
  await page.getByTestId('build-interview').waitFor()
  await page.screenshot({ path: path.join(repo, 'evidence/ui/W99-interview.png'), animations: 'disabled', timeout: 0 })
  await page.getByTestId('build-message').fill('Build a personal project hub for freelancers. It must list projects, show deadlines, and work offline. No accounts or subscriptions. Done means I can add a project and see its deadline.')
  await page.getByTestId('build-send').click()
  await page.getByText(/Who will use it/).waitFor()
  await page.getByTestId('build-understood').getByRole('button', { name: 'Review spec' }).click()
  await page.getByTestId('build-spec').waitFor()
  await page.screenshot({ path: path.join(repo, 'evidence/ui/W99-spec.png'), animations: 'disabled', timeout: 0 })
  await page.getByTestId('build-spec').getByRole('button', { name: 'Approve spec' }).click()
  await page.getByTestId('build-plan').waitFor()
  await page.screenshot({ path: path.join(repo, 'evidence/ui/W99-plan.png'), animations: 'disabled', timeout: 0 })
  check(/evaluator/.test((await page.getByTestId('build-plan').textContent()).toLowerCase()), 'plan includes an evaluator role')
  await page.getByTestId('build-plan').getByRole('button', { name: 'Approve and start team' }).click()
  await page.getByTestId('team-current-contract').waitFor()
  await page.screenshot({ path: path.join(repo, 'evidence/ui/W99-team-view.png'), animations: 'disabled', timeout: 0 })
  check(/awaiting|approval|cycle/i.test(await page.getByTestId('team-current-contract').textContent()), 'running team shows current approval contract')
  await page.getByTestId('team-current-contract').getByRole('button', { name: 'Approve' }).click()
  await page.waitForFunction(() => document.querySelector('[data-testid="screen-automations"]')?.textContent.includes('done'))
  await page.screenshot({ path: path.join(repo, 'evidence/ui/W99-completion.png'), animations: 'disabled', timeout: 0 })
  check(/PASS/.test(await page.getByTestId('team-features').textContent()), 'feature passes after evaluator completion')
  await page.getByTestId('nav-home').click()
  await page.getByTestId('home-teams').waitFor()
  await page.getByTestId('needs-you').waitFor()
  await page.screenshot({ path: path.join(repo, 'evidence/ui/W99-home.png'), animations: 'disabled', timeout: 0 })
  check(await page.getByTestId('home-team-team-1').count() === 1, 'Home lists the finished team and progress')
  check(errors.length === 0, `no browser errors (${errors.join('; ')})`)
} catch (error) { console.error(error); failures++ }
finally { await browser?.close(); cleanup() }
if (failures) process.exitCode = 1
