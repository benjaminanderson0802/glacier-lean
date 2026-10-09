// Exercise enabled semantic controls on representative routes.
// Run with: bash ~/tools/e2e.sh node e2e/every_control.spec.mjs
import { spawn } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const allowlist = JSON.parse(readFileSync(fileURLToPath(new URL('./every_control.allow.json', import.meta.url)), 'utf8'))
if (!Array.isArray(allowlist) || allowlist.some(item => !item.route || !item.selector || !item.reason)) throw new Error('allowlist entries need route, selector, and reason')
const { mockPort, uiPort, api: API, ui: UI } = await e2ePorts()
const procs = []
const start = (cmd, args, env = {}) => { const p = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true }); procs.push(p); return p }
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid, 'SIGTERM') } catch { /* already exited */ } } }
process.on('exit', cleanup)
const waitHttp = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch { /* starting */ } await new Promise(r => setTimeout(r, 200)) } throw new Error(`timeout waiting for ${url}`) }
const routes = [
  ['home', '#/home'], ['build', '#/build'], ['build/chat', '#/build/chat'],
  ['automations', '#/automations'], ['flow editor', '#/automations/build/e2e-flow'],
  ['templates', '#/automations/templates'], ['run view', '#/automations/flow/audit-flow'],
  ['memory', '#/memory'], ['note', '#/memory/projects%2Fmarket-research.md'], ['memory map', '#/memory/~map'],
  ...['general', 'models', 'secrets', 'usage', 'data', 'system', 'help', 'about'].map(section => [`settings/${section}`, `#/settings/${section}`]),
  ['claims', '#/home/claims'],
]
const selector = 'button, a[href], [role="menuitem"], [role="tab"], [role="switch"], [role="button"], [role="option"], input[type="checkbox"], select, [aria-label="Zoom In"], [aria-label="Zoom Out"], [aria-label="Fit View"]'
const normalize = value => String(value ?? '').replace(/\s+/g, ' ').trim()
const errors = [], requests = [], dead = [], failures = []
let browser
try {
  if (!existsSync(path.join(root, 'dist/index.html'))) throw new Error('dist/ missing; run npm run build first')
  start('node', ['mock/mock_server.mjs', String(mockPort)])
  await waitHttp(`${API}/api/environments`)
  start('npx', ['vite', 'preview', '--port', String(uiPort), '--strictPort'], { GLACIER_API: API })
  await waitHttp(UI)
  const executablePath = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined)
  browser = await chromium.launch(executablePath ? { executablePath } : {})
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  page.on('pageerror', error => errors.push(`page error: ${error}`))
  page.on('console', message => { if (message.type() === 'error') errors.push(`console error: ${message.text()} @ ${message.location().url}`) })
  page.on('response', response => { if (response.url().includes('/api/') && response.status() >= 400) errors.push(`API ${response.status()}: ${response.url()}`) })
  page.on('request', request => { if (request.url().includes('/api/')) requests.push(`${request.method()} ${new URL(request.url()).pathname}`) })
  page.on('dialog', dialog => { void dialog.dismiss() })
  await fetch(`${API}/api/environments/audit-flow`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ id: 'audit-flow', name: 'Audit flow', nodes: [{ id: 'n1', type: 'command', config: { cmd: 'echo test' }, position: { x: 0, y: 0 } }], edges: [] }) })
    for (const body of ['# Market research\n\nFirst audit version.', '# Market research\n\nA note for control audit.']) await fetch(`${API}/api/memory/note`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ path: 'projects/market-research.md', body, author: 'owner' }) })
    await fetch(`${API}/api/memory/note`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ path: 'runs/daily-backup.md', body: '# Daily backup\n\nCompleted successfully.', author: 'owner' }) })
  for (const id of ['weekly-report', 'inbox-triage', 'nightly-tests', 'daily-backup', 'market-research', 'e2e-flow']) {
    await fetch(`${API}/api/environments/${id}`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ id, name: id.replaceAll('-', ' '), nodes: [{ id: 'n1', type: 'command', config: { cmd: 'echo audit' }, position: { x: 0, y: 0 } }], edges: [] }) })
  }
  await fetch(`${API}/api/e2e/control-fixtures`, { method: 'POST' })

  for (const [route, hash] of routes) {
    errors.length = 0
    requests.length = 0
    await fetch(`${API}/api/environments/audit-flow`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ id: 'audit-flow', name: 'Audit flow', nodes: [{ id: 'n1', type: 'http_request', config: { method: 'GET', url: '', allowed_sites: '', headers: '', body: '', body_type: 'Text', timeout: '20', expect_status: '2xx', allow_private_network: 'No' }, position: { x: 0, y: 0 } }], edges: [] }) })
    await fetch(`${API}/api/memory/note`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ path: 'projects/market-research.md', body: '# Market research\n\nFirst version.', author: 'owner' }) })
    await fetch(`${API}/api/memory/note`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ path: 'projects/market-research.md', body: '# Market research\n\nA note for control audit.', author: 'owner' }) })
    await fetch(`${API}/api/memory/note`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ path: 'runs/daily-backup.md', body: '# Daily backup\n\nCompleted successfully.', author: 'owner' }) })
    for (const id of ['weekly-report', 'inbox-triage', 'nightly-tests', 'daily-backup', 'market-research', 'e2e-flow']) {
      await fetch(`${API}/api/environments/${id}`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ id, name: id.replaceAll('-', ' '), nodes: [{ id: 'n1', type: 'command', config: { cmd: 'echo audit' }, position: { x: 0, y: 0 } }], edges: [] }) })
    }
    await fetch(`${API}/api/e2e/control-fixtures`, { method: 'POST' })
    const url = `${UI}/${hash}`
    await page.goto(url, { waitUntil: 'networkidle' })
    await page.locator('[data-testid^="screen-"]').waitFor({ state: 'visible' })
    await page.waitForTimeout(120)
    const visited = new Set()
    while (true) {
      const current = await page.locator(selector).evaluateAll(nodes => nodes.filter(node => node instanceof HTMLElement && node.getClientRects().length > 0 && !node.closest('[aria-hidden="true"]') && !node.matches(':disabled,[aria-disabled="true"]') && !(node instanceof HTMLSelectElement && node.options.length < 2)).map(el => ({ tag: el.tagName.toLowerCase(), role: el.getAttribute('role') || '', testid: el.getAttribute('data-testid') || '', label: el.getAttribute('aria-label') || el.getAttribute('title') || el.innerText || el.textContent || '' })))
      const info = current.find(el => !visited.has(el.testid ? `id:${el.testid}` : `${el.role || el.tag}:${normalize(el.label)}`) && !(route === 'build' && /approve spec/i.test(el.label)))
      if (!info) break
      const key = info.testid ? `id:${info.testid}` : `${info.role || info.tag}:${normalize(info.label)}`
      visited.add(key)
      const label = normalize(info.label) || `${info.tag} ${info.testid}`
      const allow = allowlist.find(item => item.route === route && item.selector === (info.testid ? `[data-testid="${info.testid}"]` : `${info.role || info.tag}:${label}`))
      const before = {
        hash: await page.evaluate(() => location.hash),
        text: await page.locator('[data-testid^="screen-"]').innerText().catch(() => ''),
        dialogs: await page.locator('[role="dialog"], [aria-modal="true"], [data-testid$="-confirm"]').count(),
        requests: requests.length,
        focus: await page.evaluate(() => document.activeElement?.getAttribute('data-testid') || document.activeElement?.getAttribute('aria-label') || ''),
        errors: errors.length,
      }
      const target = info.testid ? page.getByTestId(info.testid).first() : info.role === 'option' ? page.getByRole('option', { name: normalize(info.label), exact: false }).first() : info.label ? page.locator(selector).filter({ visible: true }).filter({ hasText: normalize(info.label) }).first() : page.locator(`[aria-label="${info.label}"]`).first()
      try {
        if (info.tag === 'select') {
          await target.evaluate((element) => {
            const options = [...element.options].filter(option => !option.disabled)
            const next = options.find(option => option.value !== element.value)
            if (next) {
              element.focus()
              element.value = next.value
              element.dispatchEvent(new Event('change', { bubbles: true }))
            }
          })
        } else if (info.label === 'Zoom In' || info.label === 'Zoom Out' || info.label === 'Fit View') {
          await page.getByLabel(info.label, { exact: true }).click({ timeout: 1800 })
        } else if (info.testid === 'note-rename') {
          await target.click({ timeout: 1800 })
          await page.getByTestId('note-rename-input').fill('projects/control-audit-renamed.md')
          await page.getByTestId('note-rename-save').click()
        } else {
        // Populate empty required fields only when the control is currently disabled.
        if (await target.isDisabled().catch(() => false)) {
          const fields = page.locator('input:not([type="checkbox"]):visible, textarea:visible')
          for (let field = 0; field < await fields.count(); field++) await fields.nth(field).fill(`control audit ${field}`).catch(() => {})
        }
        await target.click({ timeout: 1800 })
        }
        await page.waitForTimeout(75)
        const after = {
          hash: await page.evaluate(() => location.hash),
          text: await page.locator('[data-testid^="screen-"]').innerText().catch(() => ''),
          dialogs: await page.locator('[role="dialog"], [aria-modal="true"], [data-testid$="-confirm"]').count(),
          focus: await page.evaluate(() => document.activeElement?.getAttribute('data-testid') || document.activeElement?.getAttribute('aria-label') || ''),
        }
        const changed = after.hash !== before.hash || after.text !== before.text || after.dialogs > before.dialogs || after.focus !== before.focus || requests.length > before.requests
        if (after.dialogs > before.dialogs || /are you sure|confirm|delete this|remove this/i.test(after.text.slice(0, 500))) {
          await page.keyboard.press('Escape').catch(() => {})
          await page.getByRole('button', { name: /cancel|keep|no|back/i }).first().click({ timeout: 400 }).catch(() => {})
        }
        if (!changed && !allow) dead.push({ route, role: info.role || info.tag, testid: info.testid, label })
        if (!changed && allow) console.log(`[every-control] allowlisted ${route}: ${label} — ${allow.reason}`)
      } catch (error) {
        failures.push(`${route}: could not activate ${label}: ${String(error).split('\n')[0]}`)
      }
      if (errors.length > before.errors) failures.push(...errors.slice(before.errors).map(error => `${route} after ${label}: ${error}`))
      await page.keyboard.press('Escape').catch(() => {})
      if (await page.evaluate(() => location.hash) !== hash) await page.goto(url, { waitUntil: 'domcontentloaded' })
      else if (await page.locator('[role="dialog"], [aria-modal="true"], [data-testid$="-confirm"]').count()) await page.goto(url, { waitUntil: 'domcontentloaded' })
      await page.locator('[data-testid^="screen-"]').waitFor({ state: 'visible' })
      if (route === 'settings/general') await page.locator('select[aria-label]').evaluateAll(selects => selects.forEach(select => select.dispatchEvent(new Event('change', { bubbles: true }))) )
      await page.waitForTimeout(30)
    }
    console.log(`[every-control] ${route}: checked ${visited.size} enabled controls`)
    if (errors.length) failures.push(...errors.map(error => `${route}: ${error}`))
  }
  if (dead.length) {
    console.error('[every-control] inert controls (screens are owned by other workers):')
    for (const item of dead) console.error(`  ${item.route} | ${item.role} | ${item.testid || '(no test id)'} | ${item.label}`)
    failures.push(`${dead.length} controls had no observable effect`)
  }
  if (failures.length) { console.error('[every-control] FAIL\n' + failures.map(item => `  ${item}`).join('\n')); process.exitCode = 1 }
  else console.log('[every-control] PASS')
} finally {
  await browser?.close()
  cleanup()
}
