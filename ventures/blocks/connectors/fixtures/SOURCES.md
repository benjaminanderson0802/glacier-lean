# Connector fixture provenance

These are static test fixtures based on response structures and examples in the official API documentation. Identifiers, names, shipment values, and license values are synthetic; the files are not captures from a customer or live account. Where the public documentation shows only a one-page example, the second fixture page is a synthetic continuation to exercise paging.

- Jobber GraphQL endpoint, account query, jobs connection and `pageInfo`: https://developer.getjobber.com/docs/using_jobbers_api/api_queries_and_mutations/
- Jobber GraphQL cost / throttle metadata and cursor pagination: https://developer.getjobber.com/docs/using_jobbers_api/api_rate_limits/
- ShipStation API v2 shipment response and page fields: https://docs.shipstation.com/list-shipments
- Shopify Admin GraphQL product edges and cursor pagination: https://shopify.dev/docs/api/admin-graphql/latest/queries/products
- Shopify GraphQL cost/rate-limit metadata: https://shopify.dev/docs/api/usage/limits
- Apify user details and dataset item array, offset/limit paging and pagination headers: https://docs.apify.com/api/v2/user-get and https://docs.apify.com/api/v2/dataset-items-get and https://docs.apify.com/api/v2
