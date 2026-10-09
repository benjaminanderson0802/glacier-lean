// Conversation renderer acceptance checks for the isolated gallery route.
import { spawn } from 'node:child_process'
import { existsSync, mkdir } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const port = 4391, ui = `http://localhost:${port}/ui-gallery-thread/`
const procs = []
const start = (cmd, args, env = {}) => {
  const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true })
  procs.push(p)
  return p
}
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch {} } }
process.on('exit', cleanup)
const waitHttp = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch {} await new Promise(r => setTimeout(r, 150)) } throw Error(`timeout ${url}`) }
let browser, failures = 0
const check = (ok, name) => { console.log(`[thread] ${ok ? 'ok  ' : 'FAIL'} ${name}`); if (!ok) failures++ }
try {
  start('npx', ['vite', '--port', String(port), '--strictPort'])
  await waitHttp(ui)
  const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(exe ? { executablePath: exe } : {})
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
  const errors = []; page.on('pageerror', e => errors.push(String(e))); page.on('console', message => { if (message.type() === 'error') errors.push(`console: ${message.text()}`) })
  await page.goto(`${ui}#/ui-gallery-thread`, { waitUntil: 'networkidle' })
  await page.getByTestId('thread-gallery').waitFor()
  const evidence = path.resolve(root, '../../evidence/ui')
  await mkdir(evidence, { recursive: true })
  await page.screenshot({ path: path.join(evidence, 'W132-message-renderer-1280x800.png'), animations: 'disabled' })
  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.screenshot({ path: path.join(evidence, 'W132-message-renderer-1920x1080.png'), animations: 'disabled' })
  await page.setViewportSize({ width: 1280, height: 800 })
  check(await page.getByText('A conversation that keeps its shape').count() === 1, 'assistant markdown renders safely')
  check(await page.locator('[data-testid="thread-message"]').count() >= 3, 'user and assistant messages render')
  await page.getByTestId('stream-demo').click()
  await page.getByRole('button', { name: 'Stop generating' }).waitFor()
  check(await page.locator('.thread-caret').count() === 1, 'streaming message shows a live caret')
  await page.getByText(/I checked the three steps/).waitFor()
  await page.getByRole('button', { name: 'Copy code' }).click()
  check(await page.getByText('Copied').count() === 1, 'code copy gives feedback')
  await page.getByRole('button', { name: 'Wrap code' }).click()
  check(await page.locator('[data-testid="code-block"][data-wrap="true"]').count() === 1, 'code wrap toggles')
  await page.getByRole('button', { name: 'Copy tool output' }).click()
  check(await page.getByTestId('tool-card').getByText('Copied').count() === 1, 'tool output can be copied')
  await page.getByRole('button', { name: 'Campaign asset packs' }).click()
  check(await page.getByRole('status').getByText('Choice sent').count() === 1, 'choice sends selected option')
  await page.getByLabel('Reason (optional)').fill('Approved for this campaign')
  await page.getByRole('button', { name: 'Approve' }).click()
  check(await page.getByTestId('approval-card').getByText('Approved').count() === 1, 'approval changes to approved state')
  check(await page.getByTestId('approval-card').getByText(/Reason: Approved for this campaign/).count() === 1, 'approval keeps its reason')
  await page.getByRole('button', { name: 'Copy message' }).first().click()
  check(await page.getByRole('status').getByText('Message copied').count() === 1, 'message action copies text')
  await page.getByRole('button', { name: 'Edit and resend' }).click()
  check(await page.getByRole('textbox', { name: 'Write a message' }).inputValue().length > 20, 'edit action places own message in the composer')
  await page.getByRole('button', { name: 'Regenerate response' }).first().click()
  check(await page.getByRole('status').getByText('A new reply is ready').count() === 1, 'regenerate action responds')
  await page.getByRole('button', { name: 'Branch from here' }).first().click()
  check(await page.getByRole('status').getByText('Started a new branch from this reply').count() === 1, 'branch action responds')
  await page.getByTestId('load-long-thread').click()
  await page.locator('[data-message-id="long-999"]').waitFor()
  check(await page.locator('[data-testid="thread-message"]').count() < 30, '1,000-message thread renders a virtual window')
  await page.getByTestId('thread-log').evaluate(node => { node.scrollTop = 0; node.dispatchEvent(new Event('scroll')) })
  await page.getByRole('button', { name: 'Jump to latest' }).waitFor()
  await page.getByRole('button', { name: 'Jump to latest' }).click()
  check(await page.getByRole('button', { name: 'Jump to latest' }).count() === 0, 'jump to latest returns to the end')
  check(errors.length === 0, `no browser errors (${errors.join('; ')})`)
} catch (error) { console.error(error); failures++ }
finally { await browser?.close(); cleanup() }
if (failures) process.exitCode = 1
