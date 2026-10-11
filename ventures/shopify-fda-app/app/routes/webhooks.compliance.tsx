import type { ActionFunctionArgs } from "react-router";
import { authenticate } from "../shopify.server";
import db from "../db.server";
import { processComplianceEvent } from "../models/compliance.server.mjs";

export const action = async ({ request }: ActionFunctionArgs) => {
  // The Shopify React Router authenticator verifies the webhook HMAC and rejects invalid requests.
  const { payload, topic, shop } = await authenticate.webhook(request);
  const result = await processComplianceEvent({ topic, shop, payload, sessionStore: db.session });
  return new Response(null, { status: result.status });
};
