import { PLANS } from './plans.mjs';

export async function createSubscriptionRequest(graphql, { plan, returnUrl, test = true }) {
  const selected = PLANS[plan];
  if (!selected) throw new Error('Unknown billing plan');
  const response = await graphql(`#graphql
    mutation GlacierCreateSubscription($name: String!, $returnUrl: URL!, $lineItems: [AppSubscriptionLineItemInput!]!, $test: Boolean!, $trialDays: Int!, $replacementBehavior: AppSubscriptionReplacementBehavior!) {
      appSubscriptionCreate(name: $name, returnUrl: $returnUrl, lineItems: $lineItems, test: $test, trialDays: $trialDays, replacementBehavior: $replacementBehavior) {
        appSubscription { id }
        confirmationUrl
        userErrors { field message }
      }
    }
  `, {
    variables: {
      name: `Glacier FDA Listing — ${selected.label}`,
      returnUrl,
      test,
      replacementBehavior: 'STANDARD',
      trialDays: 14,
      lineItems: [{ plan: { appRecurringPricingDetails: {
        price: { amount: selected.price, currencyCode: 'USD' },
        interval: 'EVERY_30_DAYS',
      } } }],
    },
  });
  const body = typeof response?.json === 'function' ? await response.json() : response;
  const result = (body?.data ?? body)?.appSubscriptionCreate;
  if (!result) throw new Error('Shopify did not return a subscription result');
  if (result.userErrors?.length) throw new Error(result.userErrors.map((item) => item.message).join('; '));
  return { id: result.appSubscription?.id ?? null, confirmationUrl: result.confirmationUrl };
}

export async function getActiveSubscription(graphql) {
  const response = await graphql(`#graphql
    query GlacierActiveSubscription {
      currentAppInstallation {
        activeSubscriptions { id name status lineItems { plan { pricingDetails { ... on AppRecurringPricing { price { amount currencyCode } interval } } } } }
      }
    }
  `);
  const body = typeof response?.json === 'function' ? await response.json() : response;
  return (body?.data ?? body)?.currentAppInstallation?.activeSubscriptions ?? [];
}

export function productLimitForSubscription(subscription) {
  if (!subscription || subscription.status !== 'ACTIVE') return 0;
  const name = String(subscription.name || '').toLowerCase();
  if (name.includes('studio')) return PLANS.studio.productLimit;
  if (name.includes('starter')) return PLANS.starter.productLimit;
  return 0;
}
