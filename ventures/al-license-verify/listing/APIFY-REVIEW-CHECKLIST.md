# Apify publishing review checklist

Official docs:

- Publish an Actor: https://docs.apify.com/actors/publishing/publish
- Store publishing terms: https://docs.apify.com/legal/store-publishing-terms-and-conditions
- Actor create/configuration fields (description, title, SEO, icon, categories): https://docs.apify.com/api/v2/actors-post
- Actor README: https://docs.apify.com/actors/publishing/actor-readme
- Input schema: https://docs.apify.com/actors/development/actor-definition/input-schema/specification/v1
- Dataset schema: https://docs.apify.com/platform/storage/dataset-schema
- Pay per event: https://docs.apify.com/actors/publishing/monetize/pay-per-event
- Actor permissions: https://docs.apify.com/actors/development/permissions

The official publishing page lists a README, logo and description, monetization, sample output, output schema, and permission level. It does not make screenshots a required field. This folder contains the paste-ready README, PNG logo asset, title/slug, short and SEO descriptions, categories/search terms, JSON sample, input/output schemas, privacy policy, pricing recommendation, and permission recommendation. The listing names and copy disclaim any government affiliation, consistent with Apify's publishing terms. The owner completes the Console review and publication.

Expected billing review: only a verified match after a successful dataset write charges `license-lookup`. Readable no-match, stale snapshot, uncertainty, malformed/unavailable files and failures are free. Disable Apify's automatic start and dataset-item events to prevent duplicate or unmatched charging.
