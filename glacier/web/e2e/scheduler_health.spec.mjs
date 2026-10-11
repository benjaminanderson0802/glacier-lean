// Home shows the durable scheduler health summary and clear next-run times.
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const port = 4338, url = `http://localhost:${port}`
let preview, browser
const check = (ok, message) => { console.log(`[scheduler-health] ${ok ? 'ok' : 'FAIL'} ${message}`); if (!ok) throw new Error(message) }
try {
  if (!existsSync(path.join(root, 'dist/index.html'))) throw new Error('dist/ missing - run npm run build first')
  preview = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), 'preview', '--port', String(port), '--strictPort'], { cwd: root, stdio: 'ignore' })
  for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) break } catch {} await new Promise(r => setTimeout(r, 200)) }
  browser = await chromium.launch((p => p ? { executablePath: p } : {})(process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : '')))
  const page = await browser.newPage()
  await page.route('**/api/home', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
    local_ai: { online: true, model: 'granite3.3:2b' }, counts: { running: 0, need_you: 0 }, needs_you: [], running: [], recent_notes: [],
    health: { date: '2026-10-09', failed_runs: 2, stuck_runs: 1, waiting_for_owner: 3, data_bytes: 2097152, note_path: 'health/glacier-health-2026-10-09.md' },
    next_runs: [{ env_id: 'daily', name: 'Daily report', next_run: '2026-10-10T09:00:00+00:00' }],
  }) }))
  await page.goto(`${url}/#/home`, { waitUntil: 'networkidle' })
  check(await page.getByTestId('health-report').count() === 1, 'daily health report is shown on Home')
  check((await page.getByTestId('health-failed').innerText()).includes('2'), 'failed run count is visible')
  check((await page.getByTestId('health-stuck').innerText()).includes('1'), 'stuck run count is visible')
  check((await page.getByTestId('next-run-daily').innerText()).includes('Daily report'), 'next run time is visible')

  await page.route('**/api/system/check', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
    cpu_cores: 4, memory_gb: 16, disk_free_gb: 20, ollama_models: [], tools: {},
    recommended: { mode: 'standard', local_model: 'granite3.3:2b', max_parallel_runs: 1 }, messages: [],
  }) }))
  await page.evaluate(() => {
    window.__startupCalls = []
    window.__TAURI__ = { core: { invoke: async (command, args) => {
      window.__startupCalls.push([command, args])
      if (command === 'supports_start_at_logon') return true
      if (command === 'get_start_at_logon') return true
      return args.enabled
    } } }
    location.hash = '#/settings/general'
  })
  const startup = page.getByTestId('start-at-logon')
  await startup.waitFor({ state: 'visible' })
  check(await startup.isChecked(), 'startup setting reflects the enabled preference')
  await startup.uncheck()
  check(await page.evaluate(() => window.__startupCalls.some(([command, args]) => command === 'set_start_at_logon' && args.enabled === false)),
    'startup setting sends a per-user preference change to the desktop shell')
} catch (error) {
  console.error('[scheduler-health] ERROR', error)
  process.exitCode = 1
} finally {
  await browser?.close()
  preview?.kill('SIGTERM')
}
if (!process.exitCode) console.log('PASS')
