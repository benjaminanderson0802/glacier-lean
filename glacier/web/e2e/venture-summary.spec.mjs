// Developer regression/capture; tester-owned ventures.spec.mjs remains unchanged.
// npm run build && node e2e/venture-summary.spec.mjs [--live]
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { existsSync, mkdtempSync, mkdirSync, writeFileSync, copyFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'
const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const root = path.resolve(web, '../..')
const evidence = path.join(root, 'docs/ui/evidence/U-VENTURES')
mkdirSync(evidence, { recursive: true })
const live = process.argv.includes('--live'), mode = live ? 'live' : 'mock'
const home = mkdtempSync(path.join(os.tmpdir(), 'u-ventures-'))
const { mockPort, uiPort, api, ui } = await e2ePorts()
const python = path.join(os.homedir(), 'w/glacier-lean/.venv/bin/python')
const env = { ...process.env, GLACIER_HOME: home, GLACIER_TOKEN: 'u-ventures-local-proof', GLACIER_API: api,
  GIT_AUTHOR_NAME: 'Glacier test', GIT_AUTHOR_EMAIL: 'test@localhost', GIT_COMMITTER_NAME: 'Glacier test', GIT_COMMITTER_EMAIL: 'test@localhost' }
// The installer reads the token file; an engine env override alone doesn't create it.
writeFileSync(path.join(home, '.engine-token'), env.GLACIER_TOKEN, { mode: 0o600 })
const processes = []
let log = ''
function start(command, args, cwd = web) {
  const child = spawn(command, args, { cwd, env, detached: true, stdio: ['ignore', 'pipe', 'pipe'] })
  child.stdout.on('data', data => { log += data.toString() })
  child.stderr.on('data', data => { log += data.toString() })
  processes.push(child)
  return child
}
async function waitFor(url) {
  for (let i = 0; i < 900; i++) {
    try { if ((await fetch(url)).ok) return } catch {}
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  throw new Error(`startup timed out: ${url}`)
}
async function request(route) {
  const response = await fetch(`${api}${route}`, { headers: { Authorization: `Bearer ${env.GLACIER_TOKEN}` } })
  assert.equal(response.status, 200)
  return response.json()
}
let browser
try {
  assert.ok(existsSync(path.join(web, 'dist/index.html')), 'build first')
  if (live) {
    start(python, ['-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', String(mockPort)], path.join(root, 'glacier/backend'))
    await waitFor(`${api}/api/health`)
    const installer = start(python, ['ventures/install_all.py', '--only', 'osha-filing', '--api', api], root)
    assert.equal(await new Promise(resolve => installer.once('exit', resolve)), 0, 'install real OSHA flows')
  } else {
    start('node', ['mock/mock_server.mjs', String(mockPort)])
    await waitFor(`${api}/api/ventures`)
  }
  start('node', ['node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1', '--port', String(uiPort), '--strictPort'])
  await waitFor(ui)
  const executablePath = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(executablePath ? { executablePath } : {})
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  page.setDefaultTimeout(30000)
  const errors = []
  page.on('pageerror', error => errors.push(String(error)))
  // The real app keeps its events socket open; wait for DOM and then the card itself.
  await page.goto(`${ui}/#/automations/ventures`, { waitUntil: 'domcontentloaded' })
  const slug = live ? 'osha-filing' : 'truck-dispatch'
  const card = page.getByTestId(`venture-${slug}`)
  await card.waitFor()
  const rows = await request('/api/ventures')
  assert.equal(await page.locator('.venture-card').count(), rows.length)
  assert.equal(await card.getByTestId(`venture-status-${slug}`).innerText(), 'blocked')
  assert.equal(await card.locator('input, select, textarea').count(), 0)
  assert.equal(await card.getByTestId(`venture-toggle-${slug}`).count(), 0)
  await page.screenshot({ path: path.join(evidence, `${mode}-portfolio-1440.png`) })
  await page.getByTestId('flow-search').fill(live ? 'osha' : 'truck')
  assert.equal(await page.locator('.venture-card').count(), 1)
  assert.ok((await card.innerText()).includes(rows.find(row => row.slug === slug).description))
  assert.equal(await card.locator('a[target="_blank"]').first().getAttribute('rel'), 'noopener noreferrer')
  await card.getByTestId(`venture-run-${slug}`).click()
  await page.waitForURL(/automations\/flow\/.+\/.+/)
  const parts = new URL(page.url()).hash.split('/')
  const runId = parts.at(-1), envId = parts.at(-2)
  assert.equal(envId, live ? 'prepare-300a' : 'dispatch-preview')
  let run
  for (let i = 0; i < 300; i++) {
    run = await request(`/api/runs/${runId}`)
    if (['waiting', 'done', 'failed'].includes(run.status)) break
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  assert.equal(run.status, live ? 'waiting' : 'done', 'owner approvals stay intact')
  await page.goto(`${ui}/#/automations/ventures`, { waitUntil: 'domcontentloaded' })
  await page.getByTestId('flow-search').fill(live ? 'osha' : 'truck')
  await card.getByTestId(`venture-last-run-${slug}`).waitFor()
  assert.ok((await card.getByTestId(`venture-last-run-${slug}`).getAttribute('href')).endsWith(runId))
  for (const [width, height] of [[1440, 900], [1280, 800]]) {
    await page.setViewportSize({ width, height })
    await page.screenshot({ path: path.join(evidence, `${mode}-venture-${width}.png`) })
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'no page overflow')
  }
  await page.getByTestId('flow-search').fill('no matching venture')
  assert.equal(await page.locator('.venture-card').count(), 0)
  assert.deepEqual(errors, [])
  writeFileSync(path.join(evidence, `${mode}-run.json`), JSON.stringify({ mode, manifest_count: rows.length, run_id: runId, env_id: envId, status: run.status, waiting_on: run.waiting_on, rows: await request('/api/ventures') }, null, 2))
  copyFileSync(path.join(web, 'src/theme/limbo/room.webp'), path.join(evidence, 'reference-room.webp'))
  console.log(`PASS ${mode}: manifests, read-only steps, search, engine run, latest result, screenshots; ${runId}: ${run.status}`)
} finally {
  await browser?.close()
  for (const child of processes.reverse()) if (child.exitCode === null) {
    try { process.kill(-child.pid, 'SIGTERM') } catch {}
  }
  writeFileSync(path.join(evidence, `${mode}-session.log`), log)
}
