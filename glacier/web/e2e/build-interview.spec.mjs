// Build interview acceptance: ask a focused question, show readiness, and draft separate EARS lines.
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const mockPort = 4387, uiPort = 4388, ui = `http://localhost:${uiPort}`
const procs = []
const start = (cmd, args, env = {}) => { const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true }); procs.push(p); return p }
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch {} } }
process.on('exit', cleanup)
const waitHttp = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch {} await new Promise(r => setTimeout(r, 150)) } throw Error(`timeout ${url}`) }
let browser
try {
  start('node', ['mock/mock_server.mjs', String(mockPort)])
  await waitHttp(`http://localhost:${mockPort}/api/teams`)
  start('npx', ['vite', 'preview', '--port', String(uiPort), '--strictPort'], { GLACIER_API: `http://localhost:${mockPort}` })
  await waitHttp(ui)
  const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(exe ? { executablePath: exe } : {})
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
  await page.goto(`${ui}/#/build`, { waitUntil: 'networkidle' })
  if (await page.getByTestId('splash').count()) await page.keyboard.press('Enter')
  await page.getByTestId('build-interview').waitFor()
  await page.getByTestId('build-message').fill('Build an offline project hub for freelancers; show deadlines and avoid accounts.')
  await page.getByTestId('build-send').click()
  await page.getByText(/offline access and no subscriptions are clear/i).waitFor()
  if (!(await page.getByTestId('build-understood').getByText(/85%/).count())) throw Error('readiness did not update from the interview')
  await page.getByTestId('build-understood').getByRole('button', { name: 'Review spec' }).click()
  const spec = page.getByTestId('build-spec')
  await spec.waitFor()
  const requirements = await spec.locator('label').filter({ hasText: 'Requirements (EARS lines)' }).locator('textarea').inputValue()
  const checks = await spec.locator('label').filter({ hasText: 'Acceptance checks' }).locator('textarea').inputValue()
  if (!requirements.includes('The system shall') || !requirements.includes('\nWhen ')) throw Error(`EARS requirements were not separate: ${requirements}`)
  if (!checks || checks.includes('Build an offline project hub')) throw Error(`acceptance check echoed the brief: ${checks}`)
  console.log('[build-interview] PASS question, readiness, and separate EARS spec')
} finally { await browser?.close(); cleanup() }
