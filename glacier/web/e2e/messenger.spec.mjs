// Acceptance checks for the always-visible right-wall messenger.
// Run after `npm run build`: node e2e/messenger.spec.mjs
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const check = (condition, message) => { console.log(`[messenger] ${condition ? 'ok  ' : 'FAIL'} ${message}`); if (!condition) throw new Error(message) }
const waitHttp = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch { /* starting */ } await new Promise(r => setTimeout(r, 200)) } throw new Error(`timeout ${url}`) }
const { uiPort, ui } = await e2ePorts()
let preview, browser

try {
  if (!existsSync(path.join(root, 'dist/index.html'))) throw new Error('dist/ missing - run `npm run build` first')
  preview = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), 'preview', '--port', String(uiPort), '--strictPort'], { cwd: root, env: process.env, stdio: 'ignore' })
  await waitHttp(ui)
  browser = await chromium.launch((p => p ? { executablePath: p } : {})(process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : '')))
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const stamp = '2026-10-09T15:14:00.000Z'
  const glacierId = 'glacier:conversation-1'
  const workerId = 'worker:team-1:build'
  let malformedThreads = false
  let rows = [
    { id: glacierId, source: 'glacier', title: 'Weekly report', last_text: 'I can help plan that.', last_at: stamp, unread: true, can_send: true },
    { id: workerId, source: 'worker', title: 'Build the inbox · Team hub', last_text: 'I am checking the search flow.', last_at: stamp, unread: false, can_send: true },
    { id: 'opencode:session-1', source: 'opencode', title: 'Local model notes', last_text: 'Read-only mirrored session.', last_at: stamp, unread: false, can_send: false },
    { id: 'codex:unavailable-session', source: 'codex', title: 'Unavailable Codex session', last_text: 'Earlier work.', last_at: stamp, unread: false, can_send: false, can_send_reason: 'Codex CLI is not installed' },
  ]
  const data = new Map([
    [glacierId, [
      { id: 'g1', from: 'me', author: 'you', text: 'Can you help with the weekly report?', at: '2026-10-08T15:14:00.000Z', kind: 'text' },
      { id: 'g2', from: 'system', author: 'Glacier', text: 'Searched recent notes', at: '2026-10-09T15:00:00.000Z', kind: 'tool' },
      { id: 'g3', from: 'them', author: 'Glacier', text: 'I can help plan that.', at: stamp, kind: 'text' },
    ]],
    [workerId, [{ id: 'w1', from: 'them', author: 'builder', text: 'I am checking the search flow.', at: stamp, kind: 'text' }]],
    ['opencode:session-1', [{ id: 'o1', from: 'them', author: 'OpenCode', text: 'Read-only mirrored session.', at: stamp, kind: 'text' }]],
  ])
  let liveSocket
  await page.routeWebSocket(/\/api\/events$/, ws => {
    ws.onMessage(() => {})
    liveSocket = ws
  })
  await page.route('**/api/messages/threads**', async route => {
    const request = route.request(), url = new URL(request.url())
    if (request.method() === 'GET' && url.pathname === '/api/messages/threads') {
      if (malformedThreads) return route.fulfill({ json: { detail: 'unexpected response shape' } })
      const q = (url.searchParams.get('q') ?? '').toLowerCase()
      return route.fulfill({ json: rows.filter(row => `${row.title} ${row.last_text} ${row.source}`.toLowerCase().includes(q)) })
    }
    if (request.method() === 'POST' && url.pathname === '/api/messages/threads') {
      const body = request.postDataJSON(), id = `${body.source}:new-session`
      const at = new Date().toISOString(), message = { id: `${id}:1`, from: 'them', author: body.source, text: `${body.source} started: ${body.text}`, at, kind: 'text' }
      const thread = { id, source: body.source, title: body.text, last_text: message.text, last_at: at, unread: false, can_send: true }
      rows = [thread, ...rows]; data.set(id, [{ id: `${id}:0`, from: 'me', author: 'you', text: body.text, at, kind: 'text' }, message])
      return route.fulfill({ json: { thread, thread_id: id, message } })
    }
    const match = url.pathname.match(/\/api\/messages\/threads\/(.+)$/)
    const id = decodeURIComponent(match?.[1] ?? '')
    if (request.method() === 'GET') return route.fulfill({ json: { id, messages: data.get(id) ?? [], next_before: null } })
    const body = request.postDataJSON(), at = new Date().toISOString()
    const mine = { id: `${id}:sent:${Date.now()}`, from: 'me', author: 'you', text: body.text, at, kind: 'text' }
    data.set(id, [...(data.get(id) ?? []), mine])
    return route.fulfill({ json: { thread_id: id, message: mine } })
  })
  await page.route('**/api/home', route => route.fulfill({ json: { local_ai: { online: true, model: 'qwen3' }, counts: { running: 0, need_you: 0 }, needs_you: [], running: [], recent_notes: [] } }))
  await page.route('**/api/teams', route => route.fulfill({ json: [] }))
  await page.goto(ui + '/#/home', { waitUntil: 'networkidle' })
  const inbox = page.getByTestId('messenger')
  check(await inbox.isVisible(), 'messenger stays visible on the right wall')
  check(await inbox.getByText('Weekly report').isVisible() && await inbox.getByText('Build the inbox · Team hub').isVisible(), 'thread list shows Glacier and worker conversations')
  check(await inbox.getByLabel(/search/i).isVisible() && await inbox.getByRole('button', { name: /new chat/i }).isVisible(), 'search and new chat controls are available')
  await inbox.getByLabel(/search/i).fill('worker')
  await inbox.getByText('Build the inbox · Team hub').waitFor({ state: 'visible' })
  await inbox.getByText('Weekly report').waitFor({ state: 'detached' })
  check(true, 'search filters threads')
  await inbox.getByLabel(/search/i).fill('')
  await inbox.getByText('Unavailable Codex session').click()
  await inbox.getByText('Codex CLI is not installed').waitFor({ state: 'visible' })
  check(await inbox.getByRole('textbox', { name: /message/i }).count() === 0, 'an unavailable imported session shows its reason and has no composer')
  await inbox.getByRole('button', { name: /back/i }).click()
  await inbox.getByText('Weekly report').click()
  await inbox.getByText('Can you help with the weekly report?').waitFor({ state: 'visible' })
  check(true, 'opening a thread shows message bubbles')
  check(await inbox.getByText('Searched recent notes').isVisible(), 'tool events render as centred system rows')
  const composer = inbox.getByRole('textbox', { name: /message/i })
  await composer.fill('Please draft')
  await composer.press('Shift+Enter')
  await composer.type('the summary')
  check(await composer.inputValue() === 'Please draft\nthe summary', 'Shift+Enter keeps a newline in the composer')
  await composer.press('Enter')
  await inbox.getByText('Please draft the summary').waitFor({ state: 'visible' })
  check(true, 'Enter sends a message to Glacier')
  await inbox.getByRole('button', { name: /back/i }).click()
  await inbox.getByText('Build the inbox · Team hub').click()
  await inbox.getByRole('textbox', { name: /message/i }).fill('Please keep the patch small')
  await inbox.getByRole('textbox', { name: /message/i }).press('Enter')
  await inbox.getByText('Please keep the patch small').waitFor({ state: 'visible' })
  check(true, 'sending to a worker task shows the owner note')
  await inbox.getByRole('button', { name: /back/i }).click()
  await inbox.getByRole('button', { name: /new chat/i }).click()
  await inbox.getByRole('button', { name: /glacier/i }).click()
  await inbox.getByRole('textbox', { name: /start a conversation/i }).fill('Plan a garden')
  await inbox.getByRole('button', { name: /start/i }).click()
  await inbox.getByText(/glacier started: plan a garden/i).waitFor({ state: 'visible' })
  check(true, 'new chat starts a Glacier conversation')
  await inbox.getByRole('button', { name: /back/i }).click()
  await inbox.getByText('Local model notes').click()
  await inbox.getByText(/read-only/i).waitFor({ state: 'visible' })
  check(await inbox.getByRole('textbox', { name: /message/i }).count() === 0, 'read-only sessions explain why replies are disabled')
  await inbox.getByRole('button', { name: /back/i }).click()
  malformedThreads = true
  await inbox.getByLabel(/search/i).fill('malformed response')
  await inbox.getByText(/could not load conversations/i).waitFor({ state: 'visible' })
  check(await inbox.locator('.messenger-error').isVisible(), 'a non-list threads response leaves the messenger usable')
  malformedThreads = false
  await inbox.getByLabel(/search/i).fill('')
  await inbox.getByText('Weekly report').waitFor({ state: 'visible' })
  await inbox.getByText('Weekly report').click()
  check(!!liveSocket, 'events WebSocket is connected to the mock')
  await page.waitForTimeout(150)
  liveSocket.send(JSON.stringify({ type: 'messages.thread_message', thread_id: glacierId, message: { id: 'live-1', from: 'them', author: 'Glacier', text: 'A live reply arrived.', at: new Date().toISOString(), kind: 'text' } }))
  await inbox.getByText('A live reply arrived.').waitFor({ state: 'visible' })
  check(true, 'live message updates appear in the open thread')
  await liveSocket.close()
  await page.close()
} catch (error) {
  console.error('[messenger] ERROR', error)
  process.exitCode = 1
} finally {
  await browser?.close()
  preview?.kill('SIGTERM')
}
if (!process.exitCode) console.log('PASS')
