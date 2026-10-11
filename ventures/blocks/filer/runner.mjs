import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const playwrightPath = path.resolve(here, '../../../glacier/web/node_modules/playwright');
const { chromium } = require(playwrightPath);

async function readInput() {
  let text = '';
  for await (const chunk of process.stdin) text += chunk;
  return JSON.parse(text);
}

async function fillAll(page, fields) {
  for (const [name, value] of Object.entries(fields)) {
    const safeName = String(name).replaceAll("\\", "\\\\").replaceAll('"', '\\"');
    const field = page.locator(`[name="${safeName}"]`);
    if (await field.count()) await field.first().fill(String(value ?? ''));
  }
}

async function main() {
  const input = await readInput();
  const browser = await chromium.launch({ headless: true });
  const context = input.storageState
    ? await browser.newContext({ storageState: input.storageState, acceptDownloads: false })
    : await browser.newContext({ acceptDownloads: false });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  try {
    if (input.operation === 'prepare') {
      await page.goto(input.baseUrl, { waitUntil: 'domcontentloaded' });
      await page.locator('input[name="username"]').fill(input.username);
      await page.locator('input[name="password"]').fill(input.password);
      const loginButton = page.locator('form[action="/login"] button').first();
      await loginButton.waitFor({ state: 'visible', timeout: 20000 });
      await loginButton.click({ timeout: 20000 });
      await page.waitForURL(/\/step\/1(?:[?#]|$)/);
      await fillAll(page, input.fields);
      await page.getByRole('button', { name: /continue|next/i }).click();
      await page.waitForURL(/\/step\/2(?:[?#]|$)/);
      await fillAll(page, input.fields);
      await page.getByRole('button', { name: /review|continue|next/i }).click();
      await page.waitForURL(/\/review(?:[?#]|$)/);
      await fillAll(page, input.fields);
      await page.screenshot({ path: input.screenshot, fullPage: true });
      const storageState = await context.storageState();
      process.stdout.write(JSON.stringify({ status: 'prepared', screenshot: input.screenshot, storageState }));
    } else if (input.operation === 'submit') {
      await page.goto(new URL('/step/1', input.baseUrl).toString(), { waitUntil: 'domcontentloaded' });
      if (/\/step\/1(?:[?#]|$)/.test(new URL(page.url()).pathname + new URL(page.url()).search)) {
        await fillAll(page, input.fields);
        await page.getByRole('button', { name: /continue|next/i }).click();
      }
      if (/\/step\/2(?:[?#]|$)/.test(new URL(page.url()).pathname + new URL(page.url()).search)) {
        await fillAll(page, input.fields);
        await page.getByRole('button', { name: /review|continue|next/i }).click();
      }
      await page.waitForURL(/\/review(?:[?#]|$)/);
      await page.getByRole('button', { name: /submit filing|submit application|submit/i }).click();
      await page.waitForURL(/\/confirmation(?:[?#]|$)/);
      const text = await page.locator('body').innerText();
      await page.screenshot({ path: input.screenshot, fullPage: true });
      await page.pdf({ path: input.pdf, format: 'A4', printBackground: true });
      process.stdout.write(JSON.stringify({ status: 'submitted', text, screenshot: input.screenshot, pdf: input.pdf }));
    } else {
      throw new Error('unknown browser operation');
    }
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write(String(error?.message || error));
  process.exitCode = 1;
});
