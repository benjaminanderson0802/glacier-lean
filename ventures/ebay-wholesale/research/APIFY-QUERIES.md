# eBay sold-listings Apify query pack

Prepared 2026-10-11 for the orchestrator. The exact Actor input payloads are in [`apify-sold-listings-queries.json`](apify-sold-listings-queries.json). Run one entry at a time with Apify Actor `blackfalcondata/ebay-sold-listings-scraper`. The Actor's published input schema documents `query`, `maxResults`, `excludeEmptyFields`, and `descriptionFormat`; this pack uses only those fields. The Actor is a community-maintained, metered service (published starting price: $4 per 1,000 listing records with details); check the current price and the owner-approved run cap before any run. [Actor input/API](https://apify.com/blackfalcondata/ebay-sold-listings-scraper/api).

## Permission gate

Benjamin has authorized Apify as the intended scraper runner. That authorization does not by itself grant permission from eBay. eBay's [User Agreement](https://www.ebay.com/help/policies/member-behavior-policies/user-agreement?id=4259) restricts automated access, including scraping, without prior express permission. eBay's [Marketplace Insights API](https://developer.ebay.com/api-docs/buy/marketplace-insights/static/overview.html) is limited release and requires eBay approval. The orchestrator must not run these queries until it has an eBay permission reference or other documented, eBay-approved access basis. Do not evade access controls, use a logged-in consumer session, rotate identities, or add proxy/bypass behavior. No query has been run and no results are claimed here.

## Query and result handling

The Actor is sold-only by its product description. Its public input does not document marketplace, condition, date-window, or best-offer filters. Therefore the query pack deliberately does not invent such input keys. After an authorized run, the orchestrator must filter returned records locally to eBay US and the trailing 90 days where the result fields support it, split new/used condition, and exclude best-offer records unless the actual paid amount is present. If the Actor output cannot reliably establish any of these fields, mark that record/query `uncertain - please check`; do not infer or substitute a sold price. The Actor may return seller identity; do not copy seller names or other personal data into venture outputs.

Capture only query, retrieval time, item ID, title, condition, item price, shipping price, sold date, model/MPN when present, and source record ID/URL. Deduplicate by item ID. Use a disclosed 30/60/90-day count and median/interquartile range only when returned fields support the calculation. An active-to-sold ratio requires a separately approved active-listing source and is a proxy, not a sell-through rate. Compare actual supplier quote and current eBay fees separately; no margin is known before both are verified.

## Exact queries

The JSON file contains the complete input payload for each query. Queries remain screening hypotheses, not validated demand. They preserve the niche ordering and model specificity in [`suppliers-and-niches.md`](suppliers-and-niches.md):

1. `72 inch skid steer grapple bucket`
2. `78 inch skid steer land planer scarifiers`
3. `6000 lb skid steer pallet forks 48 inch`
4. `commercial 2 door reach in refrigerator restaurant`
5. `commercial convection oven restaurant 208V`
6. `commercial planetary mixer 60 quart`
7. `Cummins C60D6 60kW generator A060A345`
8. `Generac 60kW commercial generator 480V 3 phase`
9. `commercial automatic transfer switch 400 amp`
10. `Kurt DX6 6 inch precision milling vise`
11. `Kurt DX8 8 inch precision milling vise`
12. `TMX 3-224-006 milling machine vise`
13. `MYCHWAY 8in1 Aristorm S Shape body contouring machine`
14. `MYCHWAY FC-23K5-US hydro dermabrasion machine`

These searches can return mixed bundles, accessories, incompatible models, or condition variants. The reviewer must exclude mismatches rather than blend them. No current sold prices, sold volume, competition count, sell-through, or wholesale margin is asserted until permitted data and written supplier terms are reviewed.
