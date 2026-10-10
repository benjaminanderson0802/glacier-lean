// The everyday data nodes remain available in the non-technical Simple layout.
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'
import { e2ePorts } from './ports.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const { mockPort, uiPort, api, ui } = await e2ePorts()
const procs = []
const start = (cmd, args, env = {}) => {
  const proc = spawn(cmd, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', detached: true })
  procs.push(proc)
  return proc
}
const cleanup = () => { for (const proc of procs.reverse()) { try { process.kill(-proc.pid, 'SIGTERM') } catch {} } }
process.on('exit', cleanup)
const waitHttp = async url => {
  for (let i = 0; i < 100; i++) {
    try { if ((await fetch(url)).status < 500) return } catch {}
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  throw Error(`timeout ${url}`)
}

let browser
try {
  start('node', ['mock/mock_server.mjs', String(mockPort)])
  await waitHttp(`http://localhost:${mockPort}/api/environments`)
  start('npx', ['vite', 'preview', '--port', String(uiPort), '--strictPort'], { GLACIER_API: api })
  await waitHttp(ui)
  const executable = process.env.CHROMIUM_PATH
  browser = await chromium.launch(executable ? { executablePath: executable } : {})
  const page = await browser.newPage()
  await page.addInitScript(() => {
    localStorage.setItem('glacier.layout', 'simple')
    localStorage.setItem('glacier.language', 'es')
  })
  await page.goto(ui + '/#/automations/build', { waitUntil: 'networkidle' })
  await page.keyboard.press('Enter')
  await page.getByTestId('new-env').click()
  await page.getByTestId('new-env-name').fill('Business data example')
  await page.getByTestId('new-env-create').click()
  for (const type of ['data_table', 'json_transform', 'csv_file', 'delay', 'structured_ai', 'email_send', 'email_read', 'email_trigger', 'for_each']) {
    if (!(await page.getByTestId(`palette-${type}`).isVisible())) throw Error(`${type} is missing from Simple layout`)
  }
  if (!(await page.getByTestId('palette-data_table').textContent()).includes('Tabla local')) throw Error('Spanish node label is missing')
  await page.getByTestId('palette-data_table').click()
  await page.getByTestId('node-n1').click()
  if (!(await page.getByTestId('field-table').isVisible())) throw Error('local table settings are missing')
  if (!(await page.getByText('Nombre de la tabla').isVisible())) throw Error('Spanish table setting is missing')
  await page.getByTestId('palette-email_send').click()
  await page.getByTestId('node-n2').click()
  if ((await page.getByTestId('field-draft_only').inputValue()) !== 'Yes') throw Error('email sending must default to draft-only')
  if (!(await page.getByText('Guardar como borrador').isVisible())) throw Error('Spanish email draft setting is missing')
  await page.getByTestId('palette-for_each').click()
  await page.getByTestId('node-n3').click()
  if (!(await page.getByTestId('field-max_items').isVisible())) throw Error('item limit setting is missing')
  if (!(await page.getByText('Máximo de elementos').isVisible())) throw Error('Spanish item limit setting is missing')
  console.log('PASS: business data nodes are discoverable and configurable in Simple layout')
} catch (error) {
  console.error(error)
  process.exitCode = 1
} finally {
  await browser?.close()
  cleanup()
}
