// Checks Limbo room geometry, readable Home content, and empty states at desktop and narrow widths.
// Run after `npm run build`: node e2e/home_polish.spec.mjs
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const UI_PORT = 4327, UI = `http://localhost:${UI_PORT}`
let preview, browser
const check = (condition, message) => { console.log(`[home] ${condition ? 'ok  ' : 'FAIL'} ${message}`); if (!condition) throw new Error(message) }
const waitHttp = async url => { for (let i = 0; i < 100; i++) { try { if ((await fetch(url)).status < 500) return } catch { /* starting */ } await new Promise(r => setTimeout(r, 200)) } throw new Error(`timeout ${url}`) }

try {
  if (!existsSync(path.join(root, 'dist/index.html'))) throw new Error('dist/ missing - run `npm run build` first')
  preview = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), 'preview', '--port', String(UI_PORT), '--strictPort'], { cwd: root, env: process.env, stdio: 'ignore' })
  await waitHttp(UI)
  browser = await chromium.launch((p => p ? { executablePath: p } : {})(process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : '')))

  for (const viewport of [{ width: 1280, height: 800 }, { width: 760, height: 700 }]) {
    const page = await browser.newPage({ viewport })
    await page.route('**/api/home', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      local_ai: { online: true, model: 'granite3.3:2b' }, counts: { running: 0, need_you: 0 }, needs_you: [], running: [], recent_notes: [],
    }) }))
    await page.goto(UI + '/#/home', { waitUntil: 'networkidle' })
    const rows = await page.evaluate(() => {
      const root = document.querySelector('[data-testid="screen-home"]')
      const stage = document.querySelector('.l-stage').getBoundingClientRect()
      const panels = ['[data-testid="game-menu"]', '.l-center', '[data-testid="side-status"]'].map(selector => {
        const rect = document.querySelector(selector).getBoundingClientRect()
        return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom }
      })
      const empty = [...root.querySelectorAll('.g-empty')]
      const row = document.createElement('div')
      row.className = 'g-row'
      row.innerHTML = '<span class="g-ico"><svg width="33" height="33"></svg></span><span class="g-mid"><span class="g-lead">A long row title</span></span><span class="g-when">now</span>'
      root.append(row)
      const icon = row.querySelector('.g-ico').getBoundingClientRect()
      const text = row.querySelector('.g-mid').getBoundingClientRect()
      return {
        stage: { left: stage.left, right: stage.right, top: stage.top, bottom: stage.bottom },
        panels,
        title: document.querySelector('.g-title').getBoundingClientRect().toJSON(),
        font: getComputedStyle(document.querySelector('.g-title')).fontFamily,
        glass: getComputedStyle(document.querySelector('.l-center')).backdropFilter,
        rowIconRight: icon.right, rowTextLeft: text.left,
        empties: empty.map(el => ({ text: el.innerText.trim(), width: el.clientWidth, scrollWidth: el.scrollWidth, height: el.clientHeight, scrollHeight: el.scrollHeight })),
      }
    })
    check(rows.panels.length === 3 && rows.panels.every(p => p.left >= rows.stage.left && p.right <= rows.stage.right && p.top >= rows.stage.top && p.bottom <= rows.stage.bottom), `${viewport.width}px: menu, screen, and status glass panels stay inside the room`)
    check(/Nunito/i.test(rows.font) && /blur\(/.test(rows.glass), `${viewport.width}px: Home uses readable Nunito text on frosted glass`)
    check(rows.title.width > 0 && rows.title.height > 0, `${viewport.width}px: Home title remains visible`)
    check(rows.rowTextLeft >= rows.rowIconRight + 2, `${viewport.width}px: Home row icon and text do not overlap`)
    check(rows.empties.length >= 3 && rows.empties.every(e => e.text && e.width > 0 && e.height > 0 && e.scrollWidth <= e.width + 1 && e.scrollHeight <= e.height + 1), `${viewport.width}px: empty states stay readable without clipping`)
    await page.close()
  }
} catch (error) {
  console.error('[home] ERROR', error)
  process.exitCode = 1
} finally {
  await browser?.close()
  preview?.kill('SIGTERM')
}
if (!process.exitCode) console.log('PASS')
