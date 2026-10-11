// Builder evidence capture against an already running disposable real backend (npm run live).
// This is a walkthrough, not the independent acceptance board. No AI engine is invoked.
import { chromium } from '../../../../glacier/web/node_modules/playwright/index.mjs'
import { writeFileSync } from 'node:fs'
const ui = process.env.ROOM_UI || 'http://127.0.0.1:18744'
const output = new URL('./', import.meta.url)
const browser = await chromium.launch()
const observations = { ui, pageErrors: [], sizes: [], events: [] }
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
  page.setDefaultTimeout(60000)
  page.on('pageerror', error => observations.pageErrors.push(String(error)))
  page.on('websocket', socket => socket.on('framereceived', frame => {
    try { const event = JSON.parse(String(frame.payload)); if (event.env_id === 'room-proof') observations.events.push(event) } catch { /* other messages */ }
  }))
  await page.goto(`${ui}/#/home`, { waitUntil: 'networkidle' })
  await page.waitForFunction(() => {
    const stage = document.querySelector('.l-stage')?.getBoundingClientRect()
    const right = document.querySelector('.l-right')?.getBoundingClientRect()
    return !!stage && !!right && right.left >= stage.left && right.right <= stage.right + 1
  })
  await page.getByTestId('room-live').and(page.locator('[data-connected="true"]')).waitFor()
  const call = async (path, data, method = 'POST') => {
    const response = await page.request.fetch(`${ui}/api/${path}`, { method, data })
    if (!response.ok()) throw new Error(`${path}: ${response.status()} ${await response.text()}`)
    return response.json()
  }
  const before = await call('home', undefined, 'GET')
  observations.beforeCounts = before.counts
  observations.activeTeamCount = (await call('teams', undefined, 'GET')).length
  const env = { id: 'room-proof', name: 'Room approval proof', nodes: [
    { id: 'prepare', type: 'command', config: { cmd: 'sleep 10; echo room-live-ready' }, position: { x: 0, y: 0 } },
    { id: 'review', type: 'approval', config: { prompt: 'Review the local room proof' }, position: { x: 240, y: 0 } },
  ], edges: [{ id: 'prepare-review', source: 'prepare', target: 'review' }] }
  await call('environments/room-proof', env, 'PUT')
  const run = await call('environments/room-proof/run', {})
  observations.runId = run.run_id
  await page.getByTestId(`room-run-${run.run_id}`).waitFor()
  // Wait for this run's own approval. The disposable home may also contain
  // unrelated starter venture inbox items, so counts are not assumed to be 1.
  let waitingRun = null
  for (let attempt = 0; attempt < 60; attempt++) {
    waitingRun = await call(`runs/${run.run_id}`, undefined, 'GET')
    if (waitingRun.status === 'waiting') break
    await page.waitForTimeout(500)
  }
  observations.waitingRun = waitingRun
  if (waitingRun?.status !== 'waiting') throw new Error(`run ${run.run_id} did not reach its approval`)
  await page.getByTestId(`room-need-run-${run.run_id}`).waitFor()
  observations.initialRun = waitingRun
  await page.screenshot({ path: new URL('live-running-1280x800.png', output).pathname })
  // Keep the centre screen simple so the screenshots expose the room and status panels.
  await page.getByTestId('nav-settings').click()
  for (const [width, height] of [[1280,800], [1440,900], [1920,1080], [2560,1440]]) {
    await page.setViewportSize({ width, height })
    await page.evaluate(() => document.fonts.ready)
    await page.waitForTimeout(400)
    observations.sizes.push(await page.evaluate(() => {
      const rect = el => { const r = el.getBoundingClientRect(); return { left: r.left, top: r.top, right: r.right, bottom: r.bottom } }
      return { width: innerWidth, height: innerHeight, stage: rect(document.querySelector('.l-stage')),
        panels: [...document.querySelectorAll('.l-left,.l-center,.l-right')].map(el => ({ ...rect(el), height: el.clientHeight, content: el.scrollHeight, transform: getComputedStyle(el).transform })),
        menu: [...document.querySelectorAll('.g-menu-list button')].map(el => ({ label: el.textContent, ...rect(el) })) }
    }))
    await page.screenshot({ path: new URL(`live-${width}x${height}.png`, output).pathname })
  }
  await page.setViewportSize({ width: 1280, height: 800 })
  await page.getByTestId('nav-home').focus()
  await page.keyboard.press('ArrowDown')
  observations.menuArrow = await page.evaluate(() => ({ focused: document.activeElement?.getAttribute('data-testid'), hash: location.hash }))
  await page.keyboard.press('End')
  observations.menuEnd = await page.evaluate(() => ({ focused: document.activeElement?.getAttribute('data-testid'), hash: location.hash, outline: getComputedStyle(document.activeElement).outlineStyle }))
  await page.screenshot({ path: new URL('keyboard-focus-1280x800.png', output).pathname })
  await page.getByTestId(`room-need-run-${run.run_id}`).click()
  observations.approvalLink = page.url()
  await page.getByTestId('run-steps').waitFor()
  // Complete only this disposable approval; no owner workflow or external action is involved.
  await call(`runs/${run.run_id}/approve`, { node_id: 'review', approved: true })
  await page.getByTestId(`room-need-run-${run.run_id}`).waitFor({ state: 'detached' })
  await page.getByTestId('room-running-count').filter({ hasText: '0' }).waitFor()
  observations.completedRun = await call(`runs/${run.run_id}`, undefined, 'GET')
  await page.screenshot({ path: new URL('live-completed-1280x800.png', output).pathname })
} finally {
  writeFileSync(new URL('live-observations.json', output), JSON.stringify(observations, null, 2))
  await browser.close()
}
