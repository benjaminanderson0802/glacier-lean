export interface CompliancePayload {
  topic: string;
  shop: string;
  payload?: unknown;
  sessionStore: { deleteMany: (args: { where: { shop: string } }) => Promise<unknown> };
}

export function processComplianceEvent(event: CompliancePayload): Promise<{ status: number }>;
export const COMPLIANCE_TOPICS: Set<string>;
