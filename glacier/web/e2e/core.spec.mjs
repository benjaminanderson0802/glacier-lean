// End-to-end test of the Glacier core v0 screen against the in-memory mock backend.
// Run from glacier/web after `npx vite build`:   node e2e/core.spec.mjs
// It starts mock/mock_server.mjs (port 8787) and `vite preview` (port 4173, proxying /api to the mock).
// Set API_URL=http://localhost:8000 and SKIP_MOCK=1 to point it at the real backend instead.
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const MOCK_PORT = 8787
const UI_PORT = Number(process.env.UI_PORT ?? 4317)
const API = process.env.API_URL ?? `http://localhost:${MOCK_PORT}`
const UI = `http://localhost:${UI_PORT}`
const procs = []
const log = (...a) => console.log('[e2e]', ...a)

function start(cmd, args, env = {}) {
  const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'], detached: true })
  p.stdout.on('data', d => process.env.E2E_VERBOSE && process.stdout.write(d))
  p.stderr.on('data', d => process.stderr.write(d))
  procs.push(p)
  return p
}
async function waitHttp(url, ms = 20000) {
  const t0 = Date.now()
  while (Date.now() - t0 < ms) {
    try { const r = await fetch(url); if (r.status < 500) return } catch { /* not up yet */ }
    await new Promise(r => setTimeout(r, 200))
  }
  throw new Error(`timeout waiting for ${url}`)
}
// kill whole process groups so the vite child of npx does not outlive the test
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch { /* gone */ } } procs.length = 0 }
process.on('exit', cleanup)

let browser
let failures = 0
const check = (cond, label) => { log(`${cond ? 'ok  ' : 'FAIL'} ${label}`); if (!cond) failures++ }

try {
  if (!existsSync(path.join(root, 'dist/index.html'))) throw new Error('dist/ missing - run `npx vite build` first')
  if (!process.env.SKIP_MOCK) start('node', ['mock/mock_server.mjs', String(MOCK_PORT)])
  await waitHttp(`${API}/api/environments`)
  start('npx', ['vite', 'preview', '--port', String(UI_PORT), '--strictPort'], { GLACIER_API: API })
  await waitHttp(UI)

  const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(exe ? { executablePath: exe } : {})
  const page = await browser.newPage({ viewport: { width: 1500, height: 900 } })
  const errors = []
  page.on('pageerror', e => errors.push(String(e)))
  page.on('console', m => { if (m.type() === 'error') errors.push(`${m.text().slice(0, 300)} @ ${m.location().url}`) })
  page.on('dialog', d => d.accept())
  const tid = id => page.getByTestId(id)

  const connect = async (from, to) => {
    const a = await tid(`handle-out-${from}`).boundingBox()
    const b = await tid(`handle-in-${to}`).boundingBox()
    await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2)
    await page.mouse.down()
    await page.mouse.move((a.x + b.x) / 2, (a.y + b.y) / 2 + 20, { steps: 8 })
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 8 })
    await page.mouse.up()
  }
  const newEnv = async name => {
    await tid('new-env').click()
    await tid('new-env-name').fill(name)
    await tid('new-env-create').click()
  }
  const waitState = (node, state, timeout = 10000) =>
    page.waitForSelector(`[data-testid="node-${node}"][data-state="${state}"]`, { timeout })

  await page.goto(UI, { waitUntil: 'networkidle' })
  await page.waitForSelector('[data-testid="ws-status"][data-connected="true"]', { timeout: 10000 })
  check(true, 'screen loaded, live events socket connected')

  // ---------- flow 1: command -> note ----------
  await newEnv('E2E flow')
  check(await tid('env-e2e-flow').isVisible(), 'new environment appears in list')
  await tid('palette-command').click()
  await tid('node-n1').click()
  await tid('field-cmd').fill('echo hello-glacier')
  await tid('palette-note').click()
  await tid('node-n2').click()
  await tid('field-path').fill('runs/{env}-{run}.md')
  await tid('field-template').fill('Run {run} of {env}: {summary}')
  await connect('n1', 'n2')
  await page.waitForSelector('.react-flow__edge', { state: 'attached', timeout: 5000 })
  check(await page.locator('.react-flow__edge').count() === 1, 'drag created one edge n1 -> n2')

  await tid('save').click()
  await page.waitForFunction(() => /^[0-9a-f]{7,}$/.test(document.querySelector('[data-testid="last-commit"]')?.textContent ?? ''))
  const commit = await tid('last-commit').textContent()
  check(true, `saved, commit ${commit}`)
  const saved = await (await fetch(`${API}/api/environments/e2e-flow`)).json()
  check(saved.nodes.length === 2 && saved.edges.length === 1 && saved.nodes[0].config.cmd === 'echo hello-glacier' && saved.edges[0].source === 'n1' && saved.edges[0].target === 'n2',
    'backend received environment with 2 nodes, 1 edge, command config')

  await tid('run').click()
  await waitState('n1', 'done')
  await waitState('n2', 'done')
  check(true, 'nodes n1, n2 turned done via live events')
  await page.waitForFunction(() => document.querySelector('[data-testid="run-status"]')?.textContent === 'done', null, { timeout: 5000 })
  check(true, 'run status shows done')
  const runId = await tid('active-run-id').textContent()
  await page.waitForSelector(`[data-testid="run-${runId}"][data-status="done"]`, { timeout: 5000 })
  check(true, 'run history lists the run as done')

  await tid('node-n1').click()
  await page.waitForSelector('[data-testid="terminal-panel"] .xterm-rows', { timeout: 5000 })
  await page.waitForFunction(() => document.querySelector('[data-testid="terminal-panel"] .xterm-rows')?.textContent.includes('hello-glacier'), null, { timeout: 5000 })
  check(true, 'clicking n1 shows its output in the xterm terminal')

  await tid('tab-vault').click()
  const notePath = `runs/e2e-flow-${runId}.md`
  await tid(`vault-note-${notePath}`).click()
  await page.waitForFunction(p => document.querySelector('[data-testid="vault-note-body"]')?.textContent.includes(p), `Run ${runId} of e2e-flow`)
  check(true, `vault lists ${notePath} and shows its body`)
  await tid('tab-canvas').click()

  // ---------- flow 2: command -> approval -(yes)-> note, approve ----------
  await newEnv('Approval flow')
  await tid('palette-command').click()
  await tid('node-n1').click()
  await tid('field-cmd').fill('echo tests passed')
  await tid('palette-approval').click()
  await tid('node-n2').click()
  await tid('field-prompt').fill('Ship it?')
  await tid('palette-note').click()
  await tid('palette-note').click()
  await connect('n1', 'n2')
  await connect('n2', 'n3')
  await connect('n2', 'n4')
  await page.waitForFunction(() => document.querySelectorAll('.react-flow__edge').length === 3)
  const labels = await page.locator('.react-flow__edge-text').allTextContents()
  check(labels.join(',') === 'yes,no', `approval out-edges auto-labelled yes/no (got ${labels})`)
  // exercise the label picker: flip e2 to "no" and e3 to "yes", then back
  await page.locator('[data-testid="rf__edge-e2"] .react-flow__edge-textwrapper').click()
  await tid('edge-label').selectOption('no')
  await page.locator('[data-testid="rf__edge-e3"] .react-flow__edge-textwrapper').click()
  await tid('edge-label').selectOption('yes')
  check((await page.locator('.react-flow__edge-text').allTextContents()).join(',') === 'no,yes', 'label picker changes yes/no')
  await tid('edge-label').selectOption('no')
  await page.locator('[data-testid="rf__edge-e2"] .react-flow__edge-textwrapper').click()
  await tid('edge-label').selectOption('yes')
  // delete n4 and its edge, then re-add a 'no' branch note via a fresh node
  await tid('node-n4').click()
  await tid('delete-selected').click()
  check(await page.locator('.react-flow__edge').count() === 2 && await tid('node-n4').count() === 0, 'delete node removes it and its edge')

  await tid('run').click() // auto-saves first
  await waitState('n1', 'done')
  await waitState('n2', 'waiting')
  await tid('approval-banner').waitFor()
  check(await tid('approval-prompt').textContent() === 'Ship it?', 'approval prompt shown')
  check(await tid('run-status').textContent() === 'waiting', 'run status waiting')
  await tid('approve').click()
  await waitState('n2', 'done')
  await waitState('n3', 'done')
  await page.waitForFunction(() => document.querySelector('[data-testid="run-status"]')?.textContent === 'done', null, { timeout: 5000 })
  check(await tid('approval-banner').count() === 0, 'approved: banner gone, n3 done, run done')

  // ---------- flow 3: reject path + history reload ----------
  await tid('run').click()
  await waitState('n2', 'waiting')
  await tid('reject').click()
  await waitState('n3', 'skipped')
  await page.waitForFunction(() => document.querySelector('[data-testid="run-status"]')?.textContent === 'rejected', null, { timeout: 5000 })
  check(true, 'rejected run: n3 skipped, status rejected')
  const firstRun = (await page.locator('[data-testid^="run-"][data-status="done"]').first().getAttribute('data-testid')).slice(4)
  await tid(`run-${firstRun}`).click()
  await page.waitForFunction(id => document.querySelector('[data-testid="active-run-id"]')?.textContent === id, firstRun)
  check(await tid('node-n3').getAttribute('data-state') === 'done', 'selecting an older run from history loads its node states')

  // ---------- flow 4: command -> Codex worker ----------
  await newEnv('Codex flow')
  await tid('palette-command').click()
  await tid('node-n1').click()
  await tid('field-cmd').fill('echo build-ok')
  check((await tid('palette-codex').textContent()).includes('Codex worker'), 'palette shows "Codex worker"')
  await tid('palette-codex').click()
  await tid('node-n2').click()
  check(await tid('field-prompt').evaluate(el => el.tagName) === 'TEXTAREA', 'codex prompt is a multi-line textarea')
  check(await tid('field-sandbox').inputValue() === 'workspace-write', 'sandbox select defaults to workspace-write')
  await tid('field-sandbox').selectOption('read-only')
  await tid('field-prompt').fill('Review {env}: {prev_output}')
  await connect('n1', 'n2')
  await page.waitForFunction(() => document.querySelectorAll('.react-flow__edge').length === 1)
  await tid('run').click() // auto-saves first
  await waitState('n2', 'done', 20000)
  await page.waitForFunction(() => document.querySelector('[data-testid="run-status"]')?.textContent === 'done', null, { timeout: 10000 })
  const cx = (await (await fetch(`${API}/api/environments/codex-flow`)).json()).nodes.find(n => n.id === 'n2')
  check(cx.type === 'codex' && cx.config.sandbox === 'read-only' && cx.config.prompt === 'Review {env}: {prev_output}', 'backend saved codex node with prompt + sandbox')
  const cxRun = await (await fetch(`${API}/api/runs/${await tid('active-run-id').textContent()}`)).json()
  check(/^codex exit 0\n/.test(cxRun.outputs.n2) && cxRun.outputs.n2.includes('Review codex-flow: ') && cxRun.outputs.n2.includes('build-ok'), `codex node done with prompt filled (got ${JSON.stringify(cxRun.outputs.n2)})`)
  await tid('node-n2').click()
  await page.waitForFunction(() => document.querySelector('[data-testid="terminal-panel"] .xterm-rows')?.textContent.includes('codex exit 0'), null, { timeout: 5000 })
  check(true, 'codex output shown in the terminal panel')

  await page.screenshot({ path: path.join(root, 'e2e/screen.png') })
  check(errors.length === 0, `no page errors${errors.length ? ': ' + errors.join(' | ') : ''}`)
} catch (e) {
  failures++
  console.error('[e2e] ERROR', e)
} finally {
  await browser?.close()
  cleanup()
}
console.log(failures ? `FAIL (${failures} failing checks)` : 'PASS')
process.exit(failures ? 1 : 0)
