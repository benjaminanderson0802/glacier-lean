export interface ActiveSubscription {
  id: string;
  name: string;
  status: string;
}

export function createSubscriptionRequest(
  graphql: (query: string, options?: { variables?: Record<string, unknown> }) => Promise<unknown>,
  options: { plan: string; returnUrl: string; test?: boolean },
): Promise<{ id: string | null; confirmationUrl: string | null }>;

export function getActiveSubscription(
  graphql: (query: string) => Promise<unknown>,
): Promise<ActiveSubscription[]>;

export function productLimitForSubscription(subscription?: ActiveSubscription): number;
