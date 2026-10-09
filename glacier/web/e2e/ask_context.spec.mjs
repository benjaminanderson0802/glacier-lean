// Ask Glacier acceptance: each supported screen sends its location and current focus to the chat API.
// Run from glacier/web after `npm run build`: node e2e/ask_context.spec.mjs
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const { mockPort, uiPort, api: API, ui: UI } = await e2ePorts()
const procs = []
const start = (cmd, args, env = {}) => {
  const child = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true })
  procs.push(child)
  return child
}
const cleanup = () => { for (const child of procs.reverse()) { try { process.kill(-child.pid, 'SIGTERM') } catch { /* already stopped */ } } }
process.on('exit', cleanup)
async function waitHttp(url) {
  const end = Date.now() + 20000
  while (Date.now() < end) { try { if ((await fetch(url)).status < 500) return } catch { /* starting */ } await new Promise(resolve => setTimeout(resolve, 200)) }
  throw new Error(`timeout waiting for ${url}`)
}

let browser
try {
  if (!existsSync(path.join(root, 'dist/index.html'))) throw new Error('dist/ missing - run `npm run build` first')
  start('node', ['mock/mock_server.mjs', String(mockPort)])
  await waitHttp(`${API}/api/health`).catch(() => waitHttp(`${API}/api/environments`))
  start('npx', ['vite', 'preview', '--port', String(uiPort), '--strictPort'], { GLACIER_API: API })
  await waitHttp(UI)
  const executablePath = existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined
  browser = await chromium.launch(executablePath ? { executablePath } : {})
  const page = await browser.newPage({ viewport: { width: 1500, height: 900 } })
  const captured = []
  await page.route(`${UI}/api/assistant/chat`, async route => {
    captured.push(JSON.parse(route.request().postData() || '{}'))
    await route.fulfill({ status: 200, headers: { 'content-type': 'text/event-stream' }, body: 'data: {"type":"RUN_STARTED"}\n\ndata: {"type":"TEXT_MESSAGE_START","messageId":"reply"}\n\ndata: {"type":"TEXT_MESSAGE_CONTENT","messageId":"reply","delta":"Ready to help."}\n\ndata: {"type":"TEXT_MESSAGE_END","messageId":"reply"}\n\ndata: {"type":"RUN_FINISHED"}\n\n' })
  })
  const check = (condition, message) => { if (!condition) throw new Error(message); console.log(`ok ${message}`) }
  const ask = async (pathName, expectedScreen, expectedFocus, label) => {
    await page.goto(`${UI}/#/${pathName}`, { waitUntil: 'networkidle' })
    await page.getByTestId('ask-glacier-open').click()
    const input = page.getByTestId('ask-glacier-input')
    await page.getByTestId('ask-glacier-context').waitFor()
    const response = page.waitForResponse(result => result.url() === `${UI}/api/assistant/chat` && result.request().method() === 'POST')
    await input.fill(`Help me with ${label}`)
    await page.getByTestId('ask-glacier-send').click()
    await response
    const request = captured.at(-1)
    check(request.screen === expectedScreen && request.focus === expectedFocus, `${label} sends screen=${expectedScreen}, focus=${expectedFocus}; got ${request.screen}/${request.focus}`)
  }
  await ask('build', 'build', 'interview', 'build interview')
  await ask('automations/build/sample-flow', 'automations/build', 'sample-flow', 'open flow')
  await ask('memory/notes/project.md', 'memory', 'notes/project.md', 'open note')
  await ask('settings/models', 'settings', 'models', 'settings section')
  await ask('automations', 'automations', '', 'automations list')
  await page.goto(`${UI}/#/settings/help`, { waitUntil: 'networkidle' })
  await page.getByTestId('ask-glacier-close').click()
  await page.keyboard.press('Control+j')
  await page.getByTestId('ask-glacier-panel').waitFor()
  check((await page.getByTestId('ask-glacier-context').innerText()).includes('settings · help'), 'Ctrl+J opens Ask Glacier with current context')
  await page.getByRole('button', { name: 'Remove screen context' }).click()
  await page.getByTestId('ask-glacier-context').waitFor({ state: 'detached' })
  const response = page.waitForResponse(result => result.url() === `${UI}/api/assistant/chat` && result.request().method() === 'POST')
  await page.getByTestId('ask-glacier-input').fill('Help me without screen context')
  await page.getByTestId('ask-glacier-send').click()
  await response
  check(captured.at(-1).screen === undefined && captured.at(-1).focus === undefined, 'removing the context chip omits screen and focus')
  check(captured.length === 6, 'six chat requests captured')
} finally {
  await browser?.close()
  cleanup()
}
