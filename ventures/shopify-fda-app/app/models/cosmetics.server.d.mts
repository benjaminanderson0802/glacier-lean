export interface CosmeticProduct {
  id: string;
  title: string;
  handle: string;
  catalogProductType: string;
  catalogTags: string[];
  ingredientsMetafield: string;
  source: string;
  result: string;
  pleaseConfirm: string[];
}

export interface ComplianceReport {
  products: CosmeticProduct[];
  hasMoreProducts: boolean;
  submitted: false;
  shopifyWrites: 0;
}

export function createComplianceReport(
  graphql: (query: string, options?: { variables?: Record<string, unknown> }) => Promise<unknown>,
): Promise<ComplianceReport>;

export const REQUIRED_BRAND_FIELDS: string[];
