const REQUIRED_BRAND_FIELDS = [
  'label name',
  'ingredients in label order',
  'product category',
  'facility and FEI or confirmed exemption',
  'responsible person',
  'first marketed date',
  'last listing date',
  'small business exemption checklist',
];

export const PRODUCTS_QUERY = `#graphql
  query CosmeticsProducts($first: Int!) {
    products(first: $first, sortKey: TITLE) {
      edges {
        node {
          id
          title
          handle
          productType
          tags
          metafields(first: 10, namespace: "custom") {
            edges { node { key value } }
          }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
`;

export async function createComplianceReport(graphql) {
  const response = await graphql(PRODUCTS_QUERY, { variables: { first: 250 } });
  const body = typeof response?.json === 'function' ? await response.json() : response;
  const data = body?.data ?? body;
  const products = data?.products?.edges ?? [];
  return {
    products: products.map(({ node }) => ({
      id: node.id,
      title: node.title,
      handle: node.handle,
      catalogProductType: node.productType || '',
      catalogTags: node.tags || [],
      ingredientsMetafield: node.metafields?.edges?.find(({ node: field }) => field.key === 'ingredients')?.node.value || '',
      source: 'Shopify product catalog',
      result: 'uncertain — please check',
      pleaseConfirm: REQUIRED_BRAND_FIELDS,
    })),
    hasMoreProducts: Boolean(data?.products?.pageInfo?.hasNextPage),
    submitted: false,
    shopifyWrites: 0,
  };
}

export { REQUIRED_BRAND_FIELDS };
