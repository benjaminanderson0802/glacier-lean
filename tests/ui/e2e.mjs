// Opens the basics screen in a headless browser and checks every piece mounted with no errors.
import { chromium } from 'playwright';
const b = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const p = await b.newPage();
const errors = [];
p.on('pageerror', e => errors.push(String(e)));
p.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
await p.goto('http://localhost:4173', { waitUntil: 'networkidle' });
const nodes = await p.locator('.react-flow__node').count();
const edges = await p.locator('.react-flow__edge').count();
const term = (await p.locator('.xterm').count()) > 0;
const editor = await p.waitForSelector('.monaco-editor', { timeout: 30000 }).then(() => true).catch(() => false);
const graph = (await p.locator('#graph canvas').count()) > 0;
await p.screenshot({ path: '../../screen.png', fullPage: true });
await b.close();
const ok = nodes === 3 && edges === 3 && term && editor && graph && errors.length === 0;
console.log(`${ok ? 'PASS' : 'FAIL'} nodes=${nodes} edges=${edges} terminal=${term} editor=${editor} graph=${graph} errors=${errors.length ? errors.join(' ; ') : 'none'}`);
process.exit(ok ? 0 : 1);
