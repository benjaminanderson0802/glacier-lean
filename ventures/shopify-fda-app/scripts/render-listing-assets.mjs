import { chromium } from 'playwright';
import { mkdir, copyFile, unlink, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const APP_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const listingDir = path.join(APP_DIR, 'listing');
const screenshotDir = path.join(listingDir, 'screenshots');
const assetsDir = path.join(listingDir, 'assets');
const reviewDir = path.join(listingDir, 'review');
const baseUrl = process.env.GLACIER_DEMO_URL || 'http://127.0.0.1:4173';

await Promise.all([mkdir(screenshotDir, { recursive: true }), mkdir(assetsDir, { recursive: true }), mkdir(reviewDir, { recursive: true })]);
const browser = await chromium.launch({ headless: true });

try {
  const context = await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  await page.goto(`${baseUrl}/app?demo=fixture`, { waitUntil: 'networkidle' });
  await page.getByText('Fixture preview only').waitFor();
  await page.screenshot({ path: path.join(screenshotDir, '01-catalog-overview.png') });

  await page.locator('input[name="last_listing_date"]').scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(screenshotDir, '02-packet-preparation.png') });

  await page.goto(`${baseUrl}/app?demo=fixture&result=uncertain`, { waitUntil: 'networkidle' });
  await page.getByText('Packet review result').scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(screenshotDir, '03-uncertain-review-result.png') });
  await context.close();

  const artPage = await browser.newPage({ viewport: { width: 1200, height: 1200 }, deviceScaleFactor: 1 });
  await artPage.setContent(iconHtml(), { waitUntil: 'load' });
  await artPage.screenshot({ path: path.join(assetsDir, 'app-icon-1200.png') });
  await artPage.setViewportSize({ width: 1600, height: 900 });
  await artPage.setContent(featureHtml(), { waitUntil: 'load' });
  await artPage.screenshot({ path: path.join(assetsDir, 'feature-image-1600x900.png') });
  await artPage.close();

  const videoContext = await browser.newContext({
    viewport: { width: 1600, height: 900 },
    recordVideo: { dir: reviewDir, size: { width: 1600, height: 900 } },
  });
  const videoPage = await videoContext.newPage();
  await videoPage.goto(`${baseUrl}/app?demo=fixture`, { waitUntil: 'networkidle' });
  await videoPage.waitForTimeout(2500);
  await videoPage.locator('input[name="label"]').scrollIntoViewIfNeeded();
  await videoPage.waitForTimeout(2500);
  await videoPage.goto(`${baseUrl}/app?demo=fixture&result=uncertain`, { waitUntil: 'networkidle' });
  await videoPage.getByText('Packet review result').scrollIntoViewIfNeeded();
  await videoPage.waitForTimeout(5000);
  const sourceVideo = await videoPage.video().path();
  await videoContext.close();
  await copyFile(sourceVideo, path.join(reviewDir, 'demo-screencast.webm'));
  await unlink(sourceVideo);
  await writeFile(path.join(reviewDir, 'demo-screencast.vtt'), `WEBVTT\n\n00:00:00.000 --> 00:00:04.000\nFixture preview: read-only Shopify catalog\n\n00:00:04.000 --> 00:00:08.000\nBrand confirms labels, ingredients, facilities, dates, and exemption details\n\n00:00:08.000 --> 00:00:14.000\nUncertain fields stay flagged. The app does not sign or submit to FDA.\n`, 'utf8');
} finally {
  await browser.close();
}

function iconHtml() { return `<!doctype html><html><head><style>
html,body{margin:0;width:100%;height:100%;background:#f3fbfb}svg{width:100%;height:100%}
</style></head><body><svg viewBox="0 0 1200 1200" role="img" aria-label="A glacier-blue folder with a clear check mark">
<rect width="1200" height="1200" rx="260" fill="#e4f6f5"/>
<path d="M245 371c0-39 32-71 71-71h206l91 94h271c39 0 71 32 71 71v363c0 39-32 71-71 71H316c-39 0-71-32-71-71V371Z" fill="#127f83"/>
<path d="M245 493h710v335c0 39-32 71-71 71H316c-39 0-71-32-71-71V493Z" fill="#15575d"/>
<path d="m438 641 106 106 225-239" fill="none" stroke="#fff" stroke-linecap="round" stroke-linejoin="round" stroke-width="62"/>
</svg></body></html>`; }

function featureHtml() { return `<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;font-family:Inter,Arial,sans-serif;color:#143c41;background:#eaf5f4}
.wrap{height:100%;padding:86px 100px;display:grid;grid-template-columns:1fr 1.08fr;gap:64px;align-items:center;background:radial-gradient(circle at 80% 15%,#d5eeee 0,#eaf5f4 55%)}
.copy{max-width:560px}.eyebrow{font-size:18px;letter-spacing:.12em;text-transform:uppercase;color:#126b72;font-weight:700}.headline{font-size:54px;line-height:1.08;margin:22px 0;color:#173c40}.body{font-size:23px;line-height:1.5;color:#416166}
.panel{background:#ffffff;border:1px solid #d1e2e1;border-radius:28px;padding:30px;box-shadow:0 24px 64px #143c4117}.bar{height:18px;width:160px;background:#d7e9e8;border-radius:9px;margin:0 0 28px}.row{display:grid;grid-template-columns:1.3fr .8fr .8fr;gap:14px;padding:20px 12px;border-bottom:1px solid #e1eceb;font-size:16px}.row.head{color:#527074;font-weight:700;background:#f4f9f8;border-radius:10px}.pill{display:inline-block;padding:7px 11px;background:#fff2d8;color:#77540b;border-radius:99px;font-size:13px;font-weight:700}.foot{margin-top:25px;padding:17px 19px;background:#f3f9f8;border-radius:14px;color:#34595d;font-size:15px}
</style></head><body><div class="wrap"><section class="copy"><div class="eyebrow">Source-linked review drafts</div><div class="headline">Prepare cosmetic listing files from your Shopify catalog.</div><div class="body">Review label details, ingredients, facility records, and dates before anything is ready to submit.</div></section><section class="panel"><div class="bar"></div><div class="row head"><span>Product</span><span>Source</span><span>Review</span></div><div class="row"><span>Example Citrus Hand Cream</span><span>Shopify catalog</span><span><span class="pill">Please check</span></span></div><div class="foot">Your responsible person reviews every field and submits any FDA filing.</div></section></div></body></html>`; }
