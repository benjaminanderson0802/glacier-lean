// Delete and Undo are inline, localized controls; the test uses only the mock backend.
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repo = path.resolve(root, '../..')
const mockPort = 8789, uiPort = 4319
const api = `http://localhost:${mockPort}`, ui = `http://localhost:${uiPort}`
const procs = []
const start = (cmd, args, env = {}) => { const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true }); procs.push(p); return p }
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch { /* gone */ } } procs.length = 0 }
process.on('exit', cleanup)
const waitHttp = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch { /* starting */ } await new Promise(r => setTimeout(r, 200)) } throw new Error(`timeout waiting for ${url}`) }
const failures = []
const check = (condition, label) => { console.log(`[delete] ${condition ? 'ok  ' : 'FAIL'} ${label}`); if (!condition) failures.push(label) }
let browser

try {
  if (!existsSync(path.join(root, 'dist/index.html'))) throw new Error('dist/ missing - run `npm run build` first')
  start('node', ['mock/mock_server.mjs', String(mockPort)])
  await waitHttp(`${api}/api/environments`)
  const headers = { 'Content-Type': 'application/json' }
  await fetch(`${api}/api/environments/w88-delete-flow`, { method: 'PUT', headers,
    body: JSON.stringify({ id: 'w88-delete-flow', name: 'W88 delete flow', nodes: [{ id: 'work', type: 'command', config: { cmd: 'true' } }], edges: [] }) })
  await fetch(`${api}/api/memory/note`, { method: 'PUT', headers,
    body: JSON.stringify({ path: 'notes/w88-delete.md', body: '# W88 note\n\nA saved note.', author: 'owner' }) })
  start('npx', ['vite', 'preview', '--port', String(uiPort), '--strictPort'], { GLACIER_API: api })
  await waitHttp(ui)
  const executable = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(executable ? { executablePath: executable } : {})
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  let dialogs = 0
  page.on('dialog', dialog => { dialogs++; void dialog.dismiss() })
  await page.goto(`${ui}/#/automations`, { waitUntil: 'networkidle' })
  await page.getByTestId('flow-w88-delete-flow').waitFor()
  mkdirSync(path.join(repo, 'evidence', 'ui'), { recursive: true })
  await page.screenshot({ path: path.join(repo, 'evidence', 'ui', 'W88-before.png'), timeout: 60000, animations: 'disabled' })
  await page.getByTestId('flow-delete-w88-delete-flow').click()
  const confirm = page.getByTestId('flow-delete-w88-delete-flow-confirm')
  await confirm.getByText('This removes the flow and its schedule; past runs stay in history.').waitFor()
  check(await confirm.isVisible(), 'flow explains what will happen before confirming')
  await page.getByTestId('flow-delete-w88-delete-flow-yes').click()
  await page.getByTestId('delete-undo-notice').waitFor()
  await page.screenshot({ path: path.join(repo, 'evidence', 'ui', 'W88-after.png'), timeout: 60000, animations: 'disabled' })
  check(await page.getByTestId('flow-w88-delete-flow').count() === 0, 'flow disappears from the list after one inline confirmation')
  await page.getByTestId('delete-undo').click()
  await page.getByTestId('flow-w88-delete-flow').waitFor()
  check(true, 'Undo restores the flow to the list')

  await page.goto(`${ui}/#/automations/build/w88-delete-flow`, { waitUntil: 'networkidle' })
  await page.getByTestId('builder-delete-flow').waitFor()
  await page.getByTestId('builder-delete-flow').click()
  await page.getByTestId('builder-delete-flow-confirm').getByText('This removes the flow and its schedule; past runs stay in history.').waitFor()
  await page.getByTestId('builder-delete-flow-yes').click()
  await page.getByTestId('delete-undo-notice').waitFor()
  check(true, 'builder also asks inline before removing a flow')
  await page.getByTestId('delete-undo').click()
  await page.getByTestId('env-name').waitFor()
  check(await page.getByTestId('env-name').inputValue() === 'W88 delete flow', 'builder Undo restores the saved flow')

  await page.getByTestId('nav-memory').click()
  await page.getByTestId('mem-note-notes/w88-delete.md').waitFor()
  await page.getByTestId('mem-delete-notes%2Fw88-delete.md').click()
  await page.getByTestId('mem-delete-notes%2Fw88-delete.md-confirm').getByText(/removes the note from Memory/).waitFor()
  await page.getByTestId('mem-delete-notes%2Fw88-delete.md-yes').click()
  await page.waitForFunction(() => !document.querySelector('[data-testid="mem-note-notes/w88-delete.md"]'))
  check(dialogs === 0, 'delete confirmation never opens a browser popup')
  check(await page.getByTestId('delete-undo-notice').isVisible(), 'note deletion offers Undo')
  await page.screenshot({ path: path.join(repo, 'evidence', 'ui', 'W88-after-note-delete.png'), timeout: 60000, animations: 'disabled' })
} catch (error) {
  console.error('[delete] FAIL', error)
  failures.push(String(error))
} finally {
  if (browser) await browser.close()
  cleanup()
}
if (failures.length) process.exitCode = 1
