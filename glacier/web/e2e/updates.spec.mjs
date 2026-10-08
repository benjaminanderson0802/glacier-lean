// Update UI acceptance flow. Run from glacier/web after `npm run build`.
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repo = path.resolve(root, '../..')
const apiPort = 8787, uiPort = 4317
const procs = []
const start = (cmd, args, cwd, env = {}) => {
  const p = spawn(cmd, args, { cwd, env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'], detached: true })
  p.stdout.on('data', d => process.env.E2E_VERBOSE && process.stdout.write(d))
  p.stderr.on('data', d => process.stderr.write(d))
  procs.push(p); return p
}
const wait = async url => {
  for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch {} await new Promise(r => setTimeout(r, 200)) }
  throw new Error(`Timed out waiting for ${url}`)
}
const cleanup = () => { for (const p of procs.reverse()) try { process.kill(-p.pid, 'SIGTERM') } catch {} }
process.on('exit', cleanup)
let browser, failures = 0
const check = (ok, label) => { console.log(`[updates] ${ok ? 'ok' : 'FAIL'} ${label}`); if (!ok) failures++ }
try {
  mkdirSync(path.join(repo, 'evidence/ui'), { recursive: true })
  start('node', ['mock/mock_server.mjs', String(apiPort)], root)
  await wait(`http://localhost:${apiPort}/api/health`).catch(() => wait(`http://localhost:${apiPort}/api/environments`))
  start('npx', ['vite', 'preview', '--port', String(uiPort), '--strictPort'], root, { GLACIER_API: `http://localhost:${apiPort}` })
  await wait(`http://localhost:${uiPort}`)
  const executable = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(executable ? { executablePath: executable } : {})
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  let installCalls = 0, checkMode = 'update'
  await page.addInitScript(() => {
    const nativeFetch = window.fetch.bind(window)
    window.fetch = (input, init) => {
      const url = typeof input === 'string' ? input : input.url
      if (url.endsWith('/api/system/check')) return Promise.resolve(new Response(JSON.stringify({ recommended: { mode: 'standard', local_model: 'granite3.3:2b', max_parallel_runs: 2 }, ollama_models: [], tools: {}, disk_free_gb: 80, memory_gb: 16, cpu_cores: 8, messages: [] }), { headers: { 'Content-Type': 'application/json' } }))
      if (url.endsWith('/api/system/settings')) return Promise.resolve(new Response(JSON.stringify({ mode: 'standard', local_model: 'granite3.3:2b', max_parallel_runs: 2, ask_route: 'unavailable' }), { headers: { 'Content-Type': 'application/json' } }))
      return nativeFetch(input, init)
    }
    window.glacierUpdater = {
      check: async () => {
        if (window.__updateCheckError) throw new Error('Network unavailable')
        return window.__updateMode === 'current' ? null : { version: '0.2.0', notes: 'Improved stability.\nFixed a startup issue.' }
      },
      install: async version => { window.__installCalled = version; await new Promise(r => setTimeout(r, 250)) },
    }
    window.addEventListener('glacier-update-available', event => { window.__GLACIER_UPDATE_NOTICE__ = event.detail })
    Object.defineProperty(window, '__setUpdateMode', { value: mode => { window.__updateMode = mode } })
    Object.defineProperty(window, '__setUpdateError', { value: value => { window.__updateCheckError = value } })
  })
  page.on('console', msg => { if (msg.type() === 'error') console.error(msg.text()) })
  await page.goto(`http://localhost:${uiPort}/#/settings/about`, { waitUntil: 'networkidle' })
  await page.locator('[data-testid="settings-about"].g-panel').waitFor()
  const before = await page.screenshot({ path: path.join(repo, 'evidence/ui/about-before.png'), fullPage: true })
  check(await page.getByTestId('settings-version').innerText().then(s => s.includes('0.1.0')), 'About shows installed version')
  await page.getByTestId('update-check').click()
  await page.getByTestId('update-install').waitFor()
  check((await page.getByTestId('update-notes').innerText()).includes('Improved stability.'), 'available version and notes are shown')
  check(await page.evaluate(() => window.__installCalled) === undefined, 'checking does not install')
  await page.screenshot({ path: path.join(repo, 'evidence/ui/about-after.png'), fullPage: true })
  await page.getByTestId('update-install').click()
  await page.getByTestId('update-restart').waitFor()
  check(await page.evaluate(() => window.__installCalled) === '0.2.0', 'install runs only after button click and asks to restart')
  await page.evaluate(() => window.__setUpdateMode('current'))
  await page.getByTestId('update-check').click()
  await page.getByTestId('update-current').waitFor()
  check(true, 'up-to-date state is shown')
  await page.evaluate(() => window.__setUpdateError(true))
  await page.getByTestId('update-check').click()
  await page.getByTestId('update-error').waitFor()
  check(true, 'plain check error is shown')
  await page.evaluate(() => window.__setUpdateError(false))

  await page.evaluate(() => { window.__setUpdateMode('update'); window.dispatchEvent(new CustomEvent('glacier-update-available', { detail: { version: '0.2.0', notes: 'Improved stability.' } })) })
  await page.getByTestId('nav-home').click()
  await page.getByTestId('home-update-notice').waitFor()
  check(true, 'startup update notice appears on Home')
  await page.getByTestId('home-update-dismiss').click()
  check(await page.getByTestId('home-update-notice').count() === 0, 'Home update notice can be dismissed')
  await page.evaluate(() => { delete window.glacierUpdater })
  await page.getByTestId('nav-settings').click()
  await page.locator('button[data-testid="settings-about"]').click()
  await page.getByTestId('update-browser').waitFor()
  check(true, 'browser explains updates are available in the desktop app')
  console.log(`[updates] screenshots: evidence/ui/about-before.png, evidence/ui/about-after.png; bytes ${before.length}`)
} catch (error) { failures++; console.error('[updates] ERROR', error) }
finally { await browser?.close(); cleanup() }
console.log(failures ? `FAIL (${failures} failing checks)` : 'PASS')
process.exit(failures ? 1 : 0)
