// Acceptance test for configuring and running the HTTP request step in Chromium.
// Run after `npx vite build`: node e2e/http_step.spec.mjs
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const { mockPort, uiPort, api, ui } = await e2ePorts()
const procs = []
const start = (cmd, args, env = {}) => { const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true }); procs.push(p); return p }
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch { /* already stopped */ } } }
process.on('exit', cleanup)
const wait = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch { /* starting */ } await new Promise(r => setTimeout(r, 200)) } throw new Error(`Timed out waiting for ${url}`) }
const check = (ok, text) => { console.log(`[http-step] ${ok ? 'ok  ' : 'FAIL'} ${text}`); if (!ok) throw new Error(text) }
let browser
try {
  if (!existsSync(path.join(root, 'dist/index.html'))) throw new Error('dist/ missing - run `npx vite build` first')
  start('node', ['mock/mock_server.mjs', String(mockPort)])
  await wait(`${api}/api/environments`)
  start('npx', ['vite', 'preview', '--port', String(uiPort), '--strictPort'], { GLACIER_API: api })
  await wait(ui)
  const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(exe ? { executablePath: exe } : {})
  const page = await browser.newPage({ viewport: { width: 1500, height: 900 } })
  await page.goto(`${ui}/#/automations/build`, { waitUntil: 'networkidle' })
  await page.getByTestId('ws-status').waitFor()
  await page.getByTestId('new-env').click()
  await page.getByTestId('new-env-name').fill('API check')
  await page.getByTestId('new-env-create').click()
  await page.getByTestId('palette-http_request').click()
  await page.getByTestId('node-n1').click()
  check(await page.getByTestId('field-method').inputValue() === 'GET', 'new step starts with GET selected')
  await page.getByTestId('field-url').fill('not a web address')
  check(/valid|http/i.test(await page.getByTestId('http-url-error').textContent()), 'invalid address gets a plain validation message')
  await page.getByTestId('field-url').fill('https://outside.example/data')
  await page.getByTestId('field-allowed_sites').fill('api.example.org')
  check(/allowed sites/i.test(await page.getByTestId('http-url-error').textContent()), 'address outside the allowed sites gets a reason')
  await page.getByTestId('field-url').fill('https://api.example.org/data')
  await page.getByTestId('field-allowed_sites').fill('api.example.org')
  await page.getByTestId('http-secret-picker').selectOption('SMTP_PASSWORD')
  check((await page.getByTestId('field-headers').inputValue()).includes('{secret:SMTP_PASSWORD}'), 'secret picker inserts its saved name without exposing a value')
  await page.getByTestId('field-method').selectOption('POST')
  await page.getByTestId('field-body_type').selectOption('JSON')
  await page.getByTestId('field-body').fill('{"note":"{prev_output}"}')
  await page.getByTestId('field-expect_status').fill('201')
  await page.getByTestId('field-url').fill('https://api.example.org/mock-api')
  await page.screenshot({ path: path.join(root, '../../evidence/ui/http-step-after.png'), fullPage: true })
  await page.getByTestId('run').click()
  await page.waitForFunction(() => document.querySelector('[data-testid="run-status"]')?.textContent === 'done', null, { timeout: 10000 })
  await page.getByTestId('node-n1').click()
  await page.getByTestId('http-result-summary').waitFor()
  const summary = await page.getByTestId('http-result-summary').textContent()
  check(/201/.test(summary) && /ms/.test(summary), 'run view shows the response status and elapsed time')
  const output = await page.getByTestId('http-result-body').textContent()
  check(/mock response/.test(output) && output.length < 2100, 'run view shows a trimmed response')
  check(!(await page.locator('body').textContent()).includes('mock-secret-value'), 'secret values never appear in the screen')
  const saved = await (await fetch(`${api}/api/environments/api-check`)).json()
  check(saved.nodes[0].config.headers.includes('{secret:SMTP_PASSWORD}') && !JSON.stringify(saved).includes('mock-secret-value'), 'saved flow contains only the secret name placeholder')
  const runId = await page.getByTestId('active-run-id').textContent()
  await page.goto(`${ui}/#/automations/flow/api-check/${runId}`, { waitUntil: 'networkidle' })
  await page.getByTestId('run-http-result-summary').waitFor()
  check(/201/.test(await page.getByTestId('run-http-result-summary').textContent()) && /ms/.test(await page.getByTestId('run-http-result-summary').textContent()), 'Run view shows the HTTP status code and response time')
  check(/mock response/.test(await page.getByTestId('run-http-result-body').textContent()), 'Run view shows the response body')
  console.log('[http-step] all acceptance checks passed')
} finally { await browser?.close(); cleanup() }
