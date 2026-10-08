import { readFile, readdir, access } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const webDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const e2eDir = path.join(webDir, 'e2e');
const packageJson = JSON.parse(await readFile(path.join(webDir, 'package.json'), 'utf8'));
let shard = null;
for (let index = 2; index < process.argv.length; index += 1) {
  if (process.argv[index] !== '--shard' || shard !== null || !process.argv[index + 1]) {
    console.error('[check-ui] usage: node scripts/check-ui.mjs [--shard i/n]');
    process.exit(2);
  }
  const match = /^(\d+)\/(\d+)$/.exec(process.argv[index + 1]);
  if (!match) {
    console.error('[check-ui] --shard must be in i/n form, with i from 1 to n');
    process.exit(2);
  }
  const [, rawIndex, rawCount] = match;
  const indexInShard = Number(rawIndex), shardCount = Number(rawCount);
  if (shardCount < 1 || indexInShard < 1 || indexInShard > shardCount) {
    console.error('[check-ui] --shard must be in i/n form, with i from 1 to n');
    process.exit(2);
  }
  shard = { index: indexInShard, count: shardCount };
  index += 1;
  if (index + 1 < process.argv.length) {
    console.error('[check-ui] usage: node scripts/check-ui.mjs [--shard i/n]');
    process.exit(2);
  }
}
const steps = [
  { name: 'theme_lint.mjs', command: 'node', args: ['e2e/theme_lint.mjs'] },
];

try {
  await access(path.join(e2eDir, 'sprite_identity.mjs'));
  steps.push({ name: 'sprite_identity.mjs', command: 'node', args: ['e2e/sprite_identity.mjs'] });
} catch {
  // This check is optional until the file is added.
}

steps.push(
  { name: 'check-i18n.mjs --fail', command: 'node', args: ['scripts/check-i18n.mjs', '--fail'] },
  { name: 'tsc -b', command: 'tsc', args: ['-b'] },
);

if (packageJson.scripts?.['render:templates']) {
  steps.push({ name: 'render:templates', command: 'npm', args: ['run', 'render:templates'] });
}

steps.push({ name: 'vite build', command: 'vite', args: ['build'] });

const specs = (await readdir(e2eDir, { withFileTypes: true }))
  .filter((entry) => entry.isFile() && entry.name.endsWith('.spec.mjs'))
  .map((entry) => entry.name)
  .sort((a, b) => {
    if (a === 'core.spec.mjs') return b === a ? 0 : -1;
    if (b === 'core.spec.mjs') return 1;
    return a.localeCompare(b);
  });

const selectedSpecs = shard
  ? specs.filter((_, index) => index % shard.count === shard.index - 1)
  : specs;
if (shard) console.log(`[check-ui] shard ${shard.index}/${shard.count}: ${selectedSpecs.length}/${specs.length} specs`);

for (const spec of selectedSpecs) {
  steps.push({ name: spec, command: 'node', args: [`e2e/${spec}`] });
}

for (let index = 0; index < steps.length; index += 1) {
  const step = steps[index];
  console.log(`[check-ui] step ${index + 1}/${steps.length} ${step.name}`);
  const result = spawnSync(step.command, step.args, {
    cwd: webDir,
    stdio: 'inherit',
    shell: process.platform === 'win32',
  });
  const exitCode = result.error ? 1 : (result.status ?? 1);
  if (exitCode !== 0) {
    console.log(`[check-ui] FAIL (${step.name})`);
    process.exit(exitCode);
  }
}

console.log('[check-ui] PASS');
