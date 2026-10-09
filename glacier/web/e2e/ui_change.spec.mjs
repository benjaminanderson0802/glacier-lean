// UI change proposals stay review-only until the owner approves them.
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const { mockPort, uiPort, api, ui } = await e2ePorts()
const procs = []
const start = (cmd, args, env = {}) => {
  const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'], detached: true })
  p.stderr.on('data', data => process.stderr.write(data))
  procs.push(p)
  return p
}
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch {} } }
process.on('exit', cleanup)
const waitHttp = async url => {
  for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch {} await new Promise(r => setTimeout(r, 150)) }
  throw Error(`timeout ${url}`)
}

if (!existsSync(path.join(root, 'dist/index.html'))) throw Error('dist/ missing - run `npm run build` first')
let browser
try {
  start('node', ['mock/mock_server.mjs', String(mockPort)])
  await waitHttp(`${api}/api/health`).catch(() => waitHttp(`${api}/api/environments`))
  start('npx', ['vite', 'preview', '--port', String(uiPort), '--strictPort'], { GLACIER_API: api })
  await waitHttp(ui)
  const executablePath = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(executablePath ? { executablePath } : {})
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
  const calls = []
  page.on('request', request => {
    if (request.url().endsWith('/api/assistant/chat')) {
      try { calls.push(JSON.parse(request.postData() ?? '{}')) } catch {}
    }
  })
  await page.goto(`${ui}/#/build/chat`, { waitUntil: 'networkidle' })

  const input = page.getByTestId('chat-input')
  await input.fill('Change this screen so the greeting is easier to read.')
  await page.getByTestId('chat-send').click()
  const card = page.getByTestId('ui-change-card').first()
  await card.waitFor()
  if (!(await card.getByTestId('ui-change-explanation').textContent()).includes('small screen change')) throw Error('plain explanation is missing')
  if (!(await card.getByTestId('ui-change-files').textContent()).includes('glacier/web/src/App.tsx')) throw Error('touched file is missing')
  await card.getByTestId('ui-change-diff').waitFor()
  await card.locator('.monaco-diff-editor').waitFor({ timeout: 15000 }).catch(() => { throw Error('proposal diff is not rendered by Monaco diff editor') })
  if (calls[0]?.screen !== 'ask' || !calls[0]?.focus) throw Error(`Ask did not send screen/focus context: ${JSON.stringify(calls[0])}`)

  await card.getByTestId('ui-change-approve').click()
  await card.getByTestId('ui-change-branch').waitFor()
  if (!(await card.getByTestId('ui-change-branch').textContent()).includes('assistant/ui-change/')) throw Error('applied branch name is missing')
  if (!(await card.getByTestId('ui-change-checks').textContent()).includes('passed')) throw Error('check results are not shown')

  await input.fill('Change this screen to make the heading clearer.')
  await page.getByTestId('chat-send').click()
  const refineCard = page.getByTestId('ui-change-card').nth(1)
  await refineCard.waitFor()
  await refineCard.getByTestId('ui-change-refine').click()
  await refineCard.getByTestId('ui-change-feedback').fill('Use a shorter heading and keep the existing color.')
  await refineCard.getByTestId('ui-change-send-feedback').click()
  await page.getByText(/You're on ask, looking at chat/i).waitFor()
  if (!calls.some(call => call.message.includes('Use a shorter heading') && call.screen === 'ask')) throw Error('refine feedback was not sent back with screen context')

  await input.fill('Change this screen to add a small hint.')
  await page.getByTestId('chat-send').click()
  const discardCard = page.getByTestId('ui-change-card').nth(2)
  await discardCard.waitFor()
  await discardCard.getByTestId('ui-change-discard').click()
  await discardCard.getByText('discarded').waitFor()

  await input.fill('Change this screen and fail checks.')
  await page.getByTestId('chat-send').click()
  const failedCard = page.getByTestId('ui-change-card').nth(3)
  await failedCard.waitFor()
  await failedCard.getByTestId('ui-change-approve').click()
  await failedCard.getByTestId('ui-change-branch').waitFor()
  if (!(await failedCard.getByTestId('ui-change-checks').textContent()).includes('failed')) throw Error('failed check result is not shown')
  console.log('[ui-change] PASS proposal review, Monaco diff, apply checks, refine context, and discard')
} finally { await browser?.close(); cleanup() }
