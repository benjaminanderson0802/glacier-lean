import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { createComplianceReport } from '../app/models/cosmetics.server.mjs';
import { createSubscriptionRequest, productLimitForSubscription } from '../app/models/billing.server.mjs';
import { processComplianceEvent } from '../app/models/compliance.server.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../../..');

async function fixture() {
  return JSON.parse(await readFile(path.join(here, '../fixtures/glacier-test-cosmetics.products.json'), 'utf8'));
}

test('only read_products is requested and the mandatory GDPR topics are configured', async () => {
  const config = await readFile(path.join(here, '../shopify.app.toml'), 'utf8');
  assert.match(config, /scopes\s*=\s*"read_products"/);
  assert.doesNotMatch(config, /write_(products|customers|orders)/);
  for (const topic of ['customers/data_request', 'customers/redact', 'shop/redact']) {
    assert.ok(config.includes(topic), `missing ${topic}`);
  }
  const webhook = await readFile(path.join(here, '../app/routes/webhooks.compliance.tsx'), 'utf8');
  assert.match(webhook, /authenticate\.webhook\(request\)/);
});

test('App Store listing copy stays within documented text limits and includes all review media', async () => {
  const listing = await readFile(path.join(here, '../listing/STORE-LISTING.md'), 'utf8');
  const intro = listing.match(/\*\*App introduction \(100-character field\):\*\* (.+)/)?.[1];
  const details = listing.match(/## App details \(500-character field\)\n\n([\s\S]+?)\n\n## Features/)?.[1];
  const featureBlock = listing.match(/## Features \(each under 80 characters\)\n\n([\s\S]+?)\n\n## Search terms/)?.[1] ?? '';
  const features = [...featureBlock.matchAll(/^- (.+)$/gm)].map((match) => match[1]);
  assert.ok(intro && intro.length <= 100, `introduction has ${intro?.length ?? 0} characters`);
  assert.ok(details && details.length <= 500, `app details have ${details?.length ?? 0} characters`);
  assert.equal(features.length, 6);
  assert.ok(features.every((feature) => feature.length <= 80));
  assert.match(listing, /\*\*Feature media alt text:\*\*/);
  assert.equal((await readdir(path.join(here, '../listing/screenshots'))).filter((name) => name.endsWith('.png')).length, 3);
  assert.ok((await readdir(path.join(here, '../listing/assets'))).includes('app-icon-1200.png'));
  assert.ok((await readdir(path.join(here, '../listing/assets'))).includes('feature-image-1600x900.png'));
  assert.ok((await readdir(path.join(here, '../listing/review'))).includes('demo-screencast.webm'));
});

test('Shopify fixture yields a source-linked review packet and does not infer filing fields', async () => {
  const response = await fixture();
  const query = async () => response.data;
  const report = await createComplianceReport(query);
  assert.equal(report.products.length, 1);
  assert.equal(report.products[0].title, 'Example Citrus Hand Cream');
  assert.equal(report.products[0].ingredientsMetafield, 'Aqua, Glycerin');
  assert.equal(report.products[0].result, 'uncertain — please check');
  assert.equal(report.products[0].source, 'Shopify product catalog');
  assert.deepEqual(report.products[0].pleaseConfirm, [
    'label name', 'ingredients in label order', 'product category', 'facility and FEI or confirmed exemption',
    'responsible person', 'first marketed date', 'last listing date', 'small business exemption checklist'
  ]);
  assert.equal(report.submitted, false);
  assert.equal(report.shopifyWrites, 0);
});

test('catalog read uses the Shopify GraphQL Admin API and never sends a mutation', async () => {
  const response = await fixture();
  const calls = [];
  const report = await createComplianceReport(async (query) => {
    calls.push(query);
    return response.data;
  });
  assert.equal(calls.length, 1);
  assert.match(calls[0], /query\s+CosmeticsProducts/);
  assert.match(calls[0], /products\(first: \$first/);
  assert.doesNotMatch(calls[0], /mutation|productUpdate|productCreate/i);
  assert.equal(report.shopifyWrites, 0);
});

test('subscription requests use Shopify Billing API recurring charges and safe test mode', async () => {
  const calls = [];
  const result = await createSubscriptionRequest(async (query, options) => {
    calls.push({ query, variables: options.variables });
    return { data: { appSubscriptionCreate: { appSubscription: { id: 'gid://shopify/AppSubscription/1' }, confirmationUrl: 'https://admin.shopify.com/confirm', userErrors: [] } } };
  }, { plan: 'starter', returnUrl: 'https://example.test/billing/return', test: true });
  assert.equal(result.confirmationUrl, 'https://admin.shopify.com/confirm');
  assert.match(calls[0].query, /appSubscriptionCreate/);
  assert.equal(calls[0].variables.name, 'Glacier FDA Listing — Starter');
  assert.equal(calls[0].variables.lineItems[0].plan.appRecurringPricingDetails.price.amount, 4.99);
  assert.equal(calls[0].variables.lineItems[0].plan.appRecurringPricingDetails.interval, 'EVERY_30_DAYS');
  assert.equal(calls[0].variables.test, true);
  assert.equal(calls[0].variables.replacementBehavior, 'STANDARD');
  assert.equal(calls[0].variables.trialDays, 14);
  assert.equal(productLimitForSubscription({ name: 'Glacier FDA Listing — Starter', status: 'ACTIVE' }), 25);
  assert.equal(productLimitForSubscription({ name: 'Glacier FDA Listing — Studio', status: 'ACTIVE' }), 250);
  assert.equal(productLimitForSubscription({ name: 'Glacier FDA Listing — Studio', status: 'DECLINED' }), 0);
});

test('compliance webhooks acknowledge requests, redact only the target shop, and are idempotent', async () => {
  const deleted = [];
  const sessionStore = { deleteMany: async ({ where }) => { deleted.push(where.shop); } };
  assert.deepEqual(await processComplianceEvent({ topic: 'customers/data_request', shop: 'fixture.myshopify.com', sessionStore }), { status: 200 });
  assert.deepEqual(await processComplianceEvent({ topic: 'customers/redact', shop: 'fixture.myshopify.com', sessionStore }), { status: 200 });
  assert.deepEqual(await processComplianceEvent({ topic: 'shop/redact', shop: 'fixture.myshopify.com', sessionStore }), { status: 200 });
  assert.deepEqual(await processComplianceEvent({ topic: 'shop/redact', shop: 'fixture.myshopify.com', sessionStore }), { status: 200 });
  assert.deepEqual(deleted, ['fixture.myshopify.com', 'fixture.myshopify.com']);
  await assert.rejects(() => processComplianceEvent({ topic: 'orders/create', shop: 'fixture.myshopify.com', sessionStore }), /Unsupported compliance webhook/);
});
