import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const APP_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const REPO_ROOT = path.resolve(APP_DIR, '../..');
const SCRIPT = path.join(APP_DIR, 'scripts', 'prepare_packet.py');

export async function prepareFdaPacket(payload, label) {
  if (!label || !Buffer.isBuffer(label.bytes) || label.bytes.length === 0) {
    throw new Error('Upload the current ingredient label to prepare a packet');
  }
  if (label.bytes.length > 10 * 1024 * 1024) throw new Error('Ingredient label must be 10 MB or smaller');
  if (!['application/pdf', 'image/png', 'image/jpeg', 'text/plain'].includes(label.type)) {
    throw new Error('Upload a PDF, PNG, JPEG, or plain text ingredient label');
  }

  const workspace = await mkdtemp(path.join(tmpdir(), 'glacier-fda-'));
  try {
    const inputPath = path.join(workspace, 'ingredient-label');
    await writeFile(inputPath, label.bytes, { mode: 0o600 });
    const result = await runPython({
      ...payload,
      ingredient_document: inputPath,
      _source_root: 'Shopify app review form',
      _field_sources: {
        product_name: 'Shopify app review form#/product_name',
        ingredients: `uploaded-label:${label.name || 'ingredient-label'}`,
      },
    }, workspace);
    if (result.packetZip) {
      result.packetZip.bytes = Buffer.from(result.packetZip.base64, 'base64');
      delete result.packetZip.base64;
    }
    return result;
  } finally {
    await rm(workspace, { recursive: true, force: true });
  }
}

function runPython(payload, workspace) {
  const executable = process.env.PYTHON_EXECUTABLE || 'python3';
  return new Promise((resolve, reject) => {
    const child = spawn(executable, [SCRIPT], {
      cwd: REPO_ROOT,
      env: { ...process.env, GLACIER_HOME: path.join(workspace, 'glacier-home') },
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
    child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) return reject(new Error(stderr.trim() || `FDA packet worker exited with status ${code}`));
      try {
        resolve(JSON.parse(stdout));
      } catch {
        reject(new Error('FDA packet worker returned an invalid response'));
      }
    });
    child.stdin.end(JSON.stringify(payload));
  });
}

export async function packetDownload(result) {
  if (!result.packetZip?.path) return null;
  return readFile(result.packetZip.path);
}
