import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createComplianceReport } from './cosmetics.server.mjs';

const APP_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

export async function getDemoReport() {
  const fixture = JSON.parse(await readFile(path.join(APP_DIR, 'fixtures/glacier-test-cosmetics.products.json'), 'utf8'));
  return createComplianceReport(async () => fixture.data);
}

export function isLocalFixtureRequest(request) {
  return process.env.NODE_ENV !== 'production'
    && process.env.GLACIER_DEMO_FIXTURE === 'true'
    && new URL(request.url).searchParams.get('demo') === 'fixture';
}
