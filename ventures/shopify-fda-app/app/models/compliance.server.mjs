const COMPLIANCE_TOPICS = new Set(['customers/data_request', 'customers/redact', 'shop/redact']);

export async function processComplianceEvent({ topic, shop, sessionStore }) {
  if (!COMPLIANCE_TOPICS.has(topic)) throw new Error('Unsupported compliance webhook');
  // Product catalog data is read on demand and is never persisted. No customer records are collected.
  // Shopify sessions are the only shop-specific records retained; shop/redact removes them.
  if (topic === 'shop/redact') await sessionStore.deleteMany({ where: { shop } });
  return { status: 200 };
}

export { COMPLIANCE_TOPICS };
