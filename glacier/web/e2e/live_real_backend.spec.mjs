// Real engine + real browser screen acceptance. Run after `npm run build` with
// `node e2e/live_real_backend.spec.mjs`; skips when the project backend venv is absent.
import { spawn } from 'node:child_process'
import { existsSync, mkdtempSync, rmSync, writeFileSync, chmodSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'
import net from 'node:net'

const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const root = path.resolve(web, '../..')
const venvPaths = process.platform === 'win32'
  ? ['Scripts/python.exe', 'Scripts/python'] : ['bin/python']
const candidates = [process.env.GLACIER_PYTHON,
  ...venvPaths.map(name => path.join(os.homedir(), 'w/glacier-lean/.venv', name)),
  ...venvPaths.map(name => path.join(root, '.venv', name)),
  ...venvPaths.map(name => path.join('/workspaces/glacier-lean/.venv', name))].filter(Boolean)
if (!candidates.some(existsSync)) {
  console.log('SKIP live real backend: project backend venv is missing (set GLACIER_PYTHON to use another venv).')
  process.exit(0)
}
if (!existsSync(path.join(web, 'dist/index.html'))) throw new Error('dist/ missing; run `npm run build` first')

async function freePort() {
  const server = net.createServer()
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve) })
  const port = server.address().port
  await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()))
  return port
}
async function waitHttp(url, timeout = 60000) {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    try { if ((await fetch(url)).ok) return } catch { /* not ready */ }
    await new Promise(resolve => setTimeout(resolve, 150))
  }
  throw new Error(`Timed out waiting for ${url}`)
}

const home = mkdtempSync(path.join(os.tmpdir(), 'glacier-live-e2e-'))
const backendPort = await freePort()
const uiPort = await freePort()
const api = `http://127.0.0.1:${backendPort}`
const ui = `http://127.0.0.1:${uiPort}`
const fakeCli = path.join(home, process.platform === 'win32' ? 'fake_chat.py' : 'fake_chat')
writeFileSync(fakeCli, `#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
output = args[args.index('-o') + 1]
with open(output, 'w', encoding='utf-8') as handle:
    json.dump({'reply': 'Real backend fake reply', 'automation': False}, handle)
`)
if (process.platform !== 'win32') chmodSync(fakeCli, 0o755)

const live = spawn(process.execPath, ['scripts/live.mjs'], {
  cwd: web,
  env: { ...process.env, GLACIER_HOME: home, GLACIER_API_PORT: String(backendPort),
    GLACIER_UI_PORT: String(uiPort), GLACIER_CHAT_BIN: fakeCli, GLACIER_ASK_ROUTE: 'codex',
    GLACIER_CODEX_SESSIONS: path.join(home, 'no-codex-sessions'),
    GLACIER_OPENCODE_DATA: path.join(home, 'no-opencode-sessions'),
    GLACIER_CLAUDE_CODE_DATA: path.join(home, 'no-claude-sessions'),
    GLACIER_GEMINI_DATA: path.join(home, 'no-gemini-sessions') },
  stdio: ['ignore', 'pipe', 'pipe'],
})
let log = ''
live.stdout.on('data', data => { log += data.toString() })
live.stderr.on('data', data => { log += data.toString() })
let browser
let failures = 0
const check = (condition, label) => {
  console.log(`${condition ? 'ok  ' : 'FAIL'} ${label}`)
  if (!condition) failures++
}
const stopLive = async () => {
  if (live.exitCode === null && live.signalCode === null) {
    live.kill('SIGTERM')
    await Promise.race([new Promise(resolve => live.once('exit', resolve)), new Promise(resolve => setTimeout(resolve, 5000))])
    if (live.exitCode === null && live.signalCode === null) live.kill('SIGKILL')
  }
  rmSync(home, { recursive: true, force: true })
}

try {
  await waitHttp(`${ui}/`)
  const browserPath = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(browserPath ? { executablePath: browserPath } : {})
  const page = await browser.newPage({ viewport: { width: 1500, height: 900 } })
  const wsEvents = []
  page.on('websocket', socket => socket.on('framereceived', frame => {
    try { wsEvents.push(JSON.parse(String(frame.payload))) } catch { /* not JSON */ }
  }))
  page.on('dialog', dialog => dialog.accept())
  const tid = id => page.getByTestId(id)
  const waitNode = (id, state) => page.waitForSelector(`[data-testid="node-${id}"][data-state="${state}"]`, { timeout: 15000 })

  await page.goto(`${ui}/#/automations/build`, { waitUntil: 'networkidle' })
  await page.waitForSelector('[data-testid="ws-status"][data-connected="true"]', { timeout: 15000 })
  check(true, 'real backend events socket connected through the Vite proxy')

  await tid('new-env').click()
  await tid('new-env-name').fill('Live real backend')
  await tid('new-env-create').click()
  await tid('palette-command').click()
  await tid('node-n1').click()
  await tid('field-cmd').fill('echo glacier-live-output')
  await tid('save').click()
  await page.waitForFunction(() => /^[0-9a-f]{7,}$/.test(document.querySelector('[data-testid="last-commit"]')?.textContent ?? ''), null, { timeout: 15000 })
  check(true, 'canvas flow saved to the real engine')
  await tid('run').click()
  await waitNode('n1', 'done')
  await page.waitForFunction(() => document.querySelector('[data-testid="run-status"]')?.textContent === 'done', null, { timeout: 15000 })
  await tid('node-n1').click()
  await page.waitForFunction(() => document.querySelector('[data-testid="terminal-panel"]')?.textContent.includes('glacier-live-output'), null, { timeout: 10000 })
  check(await tid('node-n1').getAttribute('data-state') === 'done', 'run state reached done and command output appeared in the terminal')

  await page.goto(`${ui}/#/ask/chat`, { waitUntil: 'networkidle' })
  await tid('chat-input').fill('Say hello from the live backend test')
  await tid('chat-send').click()
  await page.getByText('Real backend fake reply', { exact: true }).waitFor({ timeout: 20000 })
  check(true, 'Ask chat write completed against the real backend fake engine')

  // Reload so the messenger's initial thread query sees the Ask conversation.
  await page.reload({ waitUntil: 'networkidle' })
  await tid('messenger').waitFor({ state: 'visible', timeout: 10000 })
  const thread = page.locator('.messenger-thread-row').filter({ hasText: 'Say hello from the live backend test' })
  await thread.waitFor({ state: 'visible', timeout: 15000 })
  await thread.click()
  await page.locator('.messenger-composer textarea').fill('Follow up from the messenger panel')
  await page.locator('.messenger-composer button[type="submit"]').click()
  const messengerReply = page.locator('.messenger-bubble').filter({ hasText: 'Real backend fake reply' }).last()
  await messengerReply.waitFor({ state: 'visible', timeout: 20000 })
  const eventDeadline = Date.now() + 5000
  const sawMessengerReplyEvent = () => wsEvents.some(event =>
    event.type === 'messages.thread_message' && event.message?.text === 'Real backend fake reply')
  while (Date.now() < eventDeadline && !sawMessengerReplyEvent())
    await new Promise(resolve => setTimeout(resolve, 100))
  check(sawMessengerReplyEvent(), 'right-wall messenger reply arrived in a real backend live event')
  const sentMessengerMessage = page.locator('.messenger-log .messenger-bubble').filter({ hasText: 'Follow up from the messenger panel' }).last()
  check(await sentMessengerMessage.isVisible(), 'messenger shows the sent Glacier message')

  if (failures) console.error(`\n${failures} live real-backend check(s) failed.`)
  else console.log('\nAll live real-backend checks passed.')
} catch (error) {
  failures++
  console.error(error)
  console.error(`Live session output:\n${log}`)
} finally {
  await browser?.close()
  await stopLive()
}
process.exitCode = failures ? 1 : 0
