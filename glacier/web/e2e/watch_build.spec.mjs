// A proposed flow stays reviewable, can be refined, reveals nodes in order, saves, then runs.
import { spawn } from 'node:child_process'
import { chmodSync, existsSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import net from 'node:net'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const { mockPort, uiPort, api, ui } = await e2ePorts()
const procs = []
const start = (cmd, args, env = {}) => {
  const proc = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true })
  procs.push(proc)
}
const cleanup = () => { for (const proc of procs.reverse()) { try { process.kill(-proc.pid, 'SIGTERM') } catch {} } }
process.on('exit', cleanup)
const waitHttp = async url => {
  for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch {} await new Promise(resolve => setTimeout(resolve, 150)) }
  throw Error(`timeout ${url}`)
}
const freePort = async () => {
  const server = net.createServer()
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve) })
  const port = server.address().port
  await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()))
  return port
}

if (!existsSync(path.join(root, 'dist/index.html'))) throw Error('dist/ missing - run `npm run build` first')
let browser
let realHome
try {
  start('node', ['mock/mock_server.mjs', String(mockPort)])
  await waitHttp(`${api}/api/environments`)
  start('npx', ['vite', 'preview', '--port', String(uiPort), '--strictPort'], { GLACIER_API: api })
  await waitHttp(ui)
  const executablePath = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(executablePath ? { executablePath } : {})
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const appeared = []
  await page.exposeFunction('recordBuildNode', id => { if (!appeared.includes(id)) appeared.push(id) })
  await page.goto(`${ui}/#/automations/build`, { waitUntil: 'networkidle' })
  if (await page.getByTestId('splash').count()) await page.keyboard.press('Enter')
  await page.getByTestId('watch-build-prompt').fill('Make me a daily inbox summary')
  await page.getByTestId('watch-build-send').click()
  const proposal = page.getByTestId('proposal-overlay')
  await proposal.waitFor()
  await page.locator('.gnode.proposal-ghost[data-testid="node-fetch"]').waitFor()
  await page.locator('.gnode.proposal-ghost[data-testid="node-summarize"]').waitFor()
  if (!(await proposal.getByTestId('proposal-summary').textContent()).includes('inbox')) throw Error('proposal summary is missing')

  await proposal.getByTestId('proposal-refine-input').fill('Add a review step after the summary')
  await proposal.getByTestId('proposal-refine').click()
  await page.locator('.gnode.proposal-ghost[data-testid="node-review"]').waitFor()
  if (!(await page.locator('.gnode.proposal-changed[data-testid="node-review"]').count())) throw Error('refined step is not highlighted')

  await page.evaluate(() => {
    const root = document.querySelector('[data-testid="canvas"]')
    if (!root) throw Error('canvas missing')
    const observer = new MutationObserver(() => {
      root.querySelectorAll('[data-testid^="node-"]').forEach(node => window.recordBuildNode(node.getAttribute('data-testid').slice(5)))
    })
    observer.observe(root, { childList: true, subtree: true })
    window.buildNodeObserver = observer
  })
  await proposal.getByTestId('proposal-accept').click()
  await page.getByTestId('node-fetch').waitFor()
  await page.getByTestId('node-summarize').waitFor()
  await page.getByTestId('node-review').waitFor()
  await page.getByTestId('proposal-saved').waitFor()
  await page.getByTestId('proposal-undo').waitFor()
  const order = ['fetch', 'summarize', 'review']
  const positions = order.map(id => appeared.indexOf(id))
  if (positions.some(index => index < 0) || positions.some((index, i) => i > 0 && positions[i - 1] >= index)) {
    throw Error(`nodes did not appear in plan order: ${appeared.join(', ')}`)
  }
  await page.getByTestId('watch-build-run-once').click()
  await page.getByTestId('run-box').waitFor()
  await page.getByTestId('active-run-id').waitFor()
  console.log('[watch-build] PASS mock: propose, refine, ordered reveal, save, and run once')

  // Exercise the same browser path with the real FastAPI engine and local fake CLI adapters.
  for (const proc of procs.splice(0).reverse()) { try { process.kill(-proc.pid, 'SIGTERM') } catch {} }
  const home = realHome = mkdtempSync(path.join(os.tmpdir(), 'glacier-watch-build-'))
  const fakeEngine = path.join(home, 'fake-engine')
  writeFileSync(fakeEngine, `#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
output = args[args.index('-o') + 1]
schema = json.load(open(args[args.index('--output-schema') + 1], encoding='utf-8'))
if 'name' in schema.get('required', []):
    prompt = args[-1].lower()
    nodes = [
        {'id':'fetch','type':'command','config':[{'key':'cmd','value':'echo fetch inbox'}]},
        {'id':'summarize','type':'command','config':[{'key':'cmd','value':'echo summarize inbox'}]},
    ]
    edges = [{'source':'fetch','target':'summarize','label':''}]
    if 'review step' in prompt:
        nodes.append({'id':'review','type':'command','config':[{'key':'cmd','value':'echo review summary'}]})
        edges.append({'source':'summarize','target':'review','label':''})
    result = {'name':'Inbox summary','explanation':'A flow for your inbox summary.', 'nodes':nodes,'edges':edges,
      'acceptance':[{'kind':'human','cmd':'','question':'Is the inbox summary useful?','rubric':''}]}
else:
    result = {'reply':'I can prepare that workflow.','automation':True}
with open(output,'w',encoding='utf-8') as handle: json.dump(result,handle)
`)
  chmodSync(fakeEngine, 0o755)
  const realApiPort = await freePort(), realUiPort = await freePort()
  const realUi = `http://127.0.0.1:${realUiPort}`
  start('node', ['scripts/live.mjs'], { GLACIER_HOME: home, GLACIER_API_PORT: String(realApiPort), GLACIER_UI_PORT: String(realUiPort),
    GLACIER_CHAT_BIN: fakeEngine, GLACIER_PLANNER_BIN: fakeEngine, GLACIER_ASK_ROUTE: 'codex',
    GLACIER_CODEX_SESSIONS: path.join(home, 'no-codex-sessions'), GLACIER_OPENCODE_DATA: path.join(home, 'no-opencode-sessions'),
    GLACIER_CLAUDE_CODE_DATA: path.join(home, 'no-claude-sessions'), GLACIER_GEMINI_DATA: path.join(home, 'no-gemini-sessions') })
  await waitHttp(realUi)
  await page.goto(`${realUi}/#/automations/build`, { waitUntil: 'networkidle' })
  if (await page.getByTestId('splash').count()) await page.keyboard.press('Enter')
  await page.getByTestId('watch-build-prompt').fill('Make me a daily inbox summary')
  await page.getByTestId('watch-build-send').click()
  const realProposal = page.getByTestId('proposal-overlay')
  await realProposal.getByTestId('proposal-accept').waitFor()
  await realProposal.getByTestId('proposal-refine-input').fill('Add a review step after the summary')
  await realProposal.getByTestId('proposal-refine').click()
  await page.locator('.gnode.proposal-ghost[data-testid="node-review"]').waitFor()
  await realProposal.getByTestId('proposal-accept').click()
  await page.getByTestId('proposal-saved').waitFor()
  await page.getByTestId('proposal-undo').waitFor()
  await page.getByTestId('watch-build-run-once').click()
  await page.getByTestId('active-run-id').waitFor()
  await page.getByTestId('run-status').waitFor()
  if (!['running', 'waiting', 'done', 'failed'].includes((await page.getByTestId('run-status').textContent())?.trim() ?? '')) {
    throw Error('the started run did not show a live status')
  }
  console.log('[watch-build] PASS real backend: propose, refine, ordered reveal, apply save, undo offer, and live run status')
  await browser.close()
} finally { await browser?.close(); cleanup(); if (realHome) rmSync(realHome, { recursive: true, force: true }) }
