// Checks Home row icon columns, pixel sizing and empty states at desktop and narrow widths.
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
      const px = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--px'))
      const logo = document.querySelector('.g-brand .g-logo')
      const brand = document.querySelector('.g-brand-name')
      const title = document.querySelector('.g-title')
      const empty = [...root.querySelectorAll('.g-empty')]
      const row = document.createElement('div')
      row.className = 'g-row'
      row.innerHTML = '<span class="g-ico"><svg width="33" height="33"></svg></span><span class="g-mid"><span class="g-lead">A long row title</span></span><span class="g-when">now</span>'
      root.append(row)
      const icon = row.querySelector('.g-ico').getBoundingClientRect()
      const text = row.querySelector('.g-mid').getBoundingClientRect()
      return {
        px,
        titleSize: parseFloat(getComputedStyle(title).fontSize),
        brandSize: parseFloat(getComputedStyle(brand).fontSize),
        logo: { width: logo.getBoundingClientRect().width, height: logo.getBoundingClientRect().height },
        gap: parseFloat(getComputedStyle(document.querySelector('.g-brand')).gap),
        rowIconRight: icon.right, rowTextLeft: text.left,
        empties: empty.map(el => ({ justify: getComputedStyle(el).justifyContent, align: getComputedStyle(el).alignItems, icon: !!el.querySelector('.g-status'), textColor: getComputedStyle(el).color, children: el.children.length })),
      }
    })
    const unit = rows.px
    check(rows.rowTextLeft >= rows.rowIconRight + 2 * unit, `${viewport.width}px: fixed row icon column has a gap before text`)
    check([8 * unit, 16 * unit].includes(rows.titleSize) && [8 * unit, 16 * unit].includes(rows.brandSize), `${viewport.width}px: Home title and title bar use 8px/16px grid sizes`)
    check(rows.logo.height === 8 * unit && rows.logo.width === 13 * unit && rows.gap >= unit, `${viewport.width}px: title logo is integer-scaled, centred and separated`)
    check(rows.empties.length >= 3 && rows.empties.every(e => e.justify === 'center' && e.align === 'center' && e.icon && e.children === 2), `${viewport.width}px: all empty states center an icon and dim line`)
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
