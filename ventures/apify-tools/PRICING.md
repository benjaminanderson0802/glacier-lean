# Apify launch pricing — 2026-10-10 Alabama / 2026-10-11 UTC

These are owner-review recommendations, not changes to live billing. Source: unauthenticated GET requests to the [Apify Store API](https://api.apify.com/v2/store), retrieved at 02:51 UTC; exact URLs and complete responses are saved with timestamps in [the evidence directory](../research/a-cash-evidence/). No Actor was run or purchased during this research.

## Competitor prices and adoption

All eight below returned `PAY_PER_EVENT`. Statistics are **lifetime runs / lifetime users / 30-day users / 30-day public runs**. FREE and BRONZE are Apify subscription pricing tiers, not free-of-charge events. Table includes every charge event in each selected listing, including startup charges; review the API snapshot for remaining tier discounts and minimum-charge settings. Startup event counts can scale with allocated memory.

| Actor (adjacent competitor; not a tested endorsement) | Runs / users / recent users / public runs | USD per event | Primary evidence |
|---|---:|---|---|
| [parseforge/cslb-california-scraper](https://apify.com/parseforge/cslb-california-scraper) | 1,453 / 104 / 6 / 60 | `result-item` $0.025 FREE / $0.02367 BRONZE; `apify-actor-start` $0.0055 FREE / $0.00533 BRONZE | [API snapshot](../research/a-cash-evidence/contractor-license.json) |
| [pink_comic/cslb-contractor-license-search](https://apify.com/pink_comic/cslb-contractor-license-search) | 3,953 / 60 / 14 / 575 | `apify-actor-start` $0.0001; `apify-default-dataset-item` $0.002 | [API snapshot](../research/a-cash-evidence/contractor-license.json) |
| [stackrelay/az-roc-license-scraper](https://apify.com/stackrelay/az-roc-license-scraper) | 250 / 7 / 2 / 49 | `apify-default-dataset-item` $0.0065 FREE / $0.006 BRONZE; `apify-actor-start` $5e-05 | [API snapshot](../research/a-cash-evidence/contractor-license.json) |
| [parsebird/buildzoom-scraper](https://apify.com/parsebird/buildzoom-scraper) | 567 / 40 / 1 / 30 | `apify-actor-start` $5e-05; `buildzoom-contractor-listing` $0.004; `buildzoom-contractor-detail` $0.007 | [API snapshot](../research/a-cash-evidence/contractor-license.json) |
| [night111/product-recall-impact-matcher](https://apify.com/night111/product-recall-impact-matcher) | 56 / 2 / 1 / 26 | `apify-actor-start` $4e-05; `actionable-insight` $0.01751 FREE / $0.015759 BRONZE | [API snapshot](../research/a-cash-evidence/product-recall.json) |
| [tictechid/vanzi-us-recall-intelligence](https://apify.com/tictechid/vanzi-us-recall-intelligence) | 49 / 2 / 2 / 6 | `apify-actor-start` $0.001 FREE / $0.0008 BRONZE; `apify-default-dataset-item` $0.005 FREE / $0.003 BRONZE; `include-analytics` $0.001 FREE / $0.001 BRONZE | [API snapshot](../research/a-cash-evidence/product-recall.json) |
| [flash_scraper/fda-recall-scraper](https://apify.com/flash_scraper/fda-recall-scraper) | 120 / 2 / 1 / 26 | `apify-actor-start` $5e-05; `apify-default-dataset-item` $0.008 | [API snapshot](../research/a-cash-evidence/product-recall.json) |
| [texxupport/cpsc-recall-monitor](https://apify.com/texxupport/cpsc-recall-monitor) | 175 / 2 / 1 / 6 | `apify-actor-start` $5e-05; `apify-default-dataset-item` $1e-05; `recall-record` $0.004 | [API snapshot](../research/a-cash-evidence/product-recall.json) |

Searches: [contractor license](https://api.apify.com/v2/store?search=contractor%20license&limit=100&sortBy=popularity) returned 265 results; [product recall](https://api.apify.com/v2/store?search=product%20recall&limit=100&sortBy=popularity) 200; [FDA recall](https://api.apify.com/v2/store?search=FDA%20recall&limit=100&sortBy=popularity) 183; [CPSC](https://api.apify.com/v2/store?search=CPSC&limit=100&sortBy=popularity) 414. Only the first 100 per query were captured; relevance was checked manually for this table. Broad search results include unrelated keyword tools. These totals do not measure competition in one state, market size or paying demand. [Owner-name search](https://api.apify.com/v2/store?search=anderson-data-tools&limit=100&sortBy=popularity) returned zero; that does not verify whether private Actors exist.

[API field definitions](https://docs.apify.com/api/v2/store-get) say lifetime users include the owner; public 30-day run counts exclude owner runs. Runs still do not establish paid use, successful fulfillment, unique buyers or profit. Some responses show public runs alongside zero recent users; retain those values rather than interpreting them as revenue. California and Arizona license tools are adjacent evidence, not direct Mississippi/Louisiana equivalents. FDA record extraction and inventory matching have different billing units.

## Recommended event settings

| Repo Actor | Event | Proposed USD/query | 100 billable queries | Reason |
|---|---|---:|---:|---|
| [Mississippi](.actor/README.md) | `license-lookup` | $0.02 | $2.00 | Retain existing draft price: narrow board parsing plus source provenance; below parseforge's FREE-tier record price but above cheaper bulk tools. No proof of premium willingness to pay yet. |
| [Louisiana](../apify-tools-louisiana/.actor/README.md) | `license-lookup` | $0.02 | $2.00 | Same unit and existing draft price as Mississippi; multiple matches from one name search cost one event. |
| [Recall](../recall-actor/.actor/README.md) | `recall-check` | $0.01 | $1.00 | Retain requested price. Several official sources per query; between low-price recall extraction and the adjacent $0.01751 matching tool. This is a test, not evidence of superiority. |
| [Alabama uploaded roster](../al-license-verify/.actor/README.md) | `license-lookup` | $0.01 | $1.00 | Customer supplies the dataset and processing is local to the run; $0.05 in the older pilot hypothesis is hard to defend against cheap record tools and a spreadsheet. Keep publication on hold until an authorized roster path is confirmed. |

Use PPE with platform usage included. Proposed additional events: none; disable `apify-default-dataset-item` and automatic startup billing so examples above stay true. Only the owner can configure, deploy or publish. A README does not configure a price. No new subscription or paid API is required or approved.

Code audit: both state runners charge once per query unless the first result is `unverifiable`; readable no-matches and incomplete/uncertain records can be charged. Alabama charges every output except `unverifiable`, including old-snapshot uncertainty. Recall excludes only outage-only results (errors with no successful source); partial success and uncertainty can be charged. Do not advertise “pay only for matches.” Event idempotency is within a run; a rerun can bill again. Runners do not explicitly stop on `ChargeResult`; do not advertise that setting a dollar limit stops all processing. Owner must verify a low-limit run before release; this card changes no billing code.

## Unit economics and decision rules

[Apify's PPE documentation](https://docs.apify.com/actors/publishing/monetize/pay-per-event) defines developer profit as 80% of paid-plan event revenue less platform cost; free-plan use does not earn developer revenue. At $0.02, contribution before compute is $0.016/query; at $0.01 it is $0.008. Measure actual compute before publication: a target of at least 50% contribution on gross revenue implies cost <=$0.006/license query or <=$0.003/recall or roster query. These are proposed targets, not measured costs.

A $49 direct pilot equals 2,450 events at $0.02 or 4,900 at $0.01 in gross sales. At zero compute cost, a $20 payout requires at least 1,250 eligible $0.02 events or 2,500 eligible $0.01 events; actual requirements are higher. One sale on Apify does not put $1 in the bank.

[Monthly payouts](https://docs.apify.com/actors/publishing/monetize/monthly-payouts) are issued on days 21–25 for the prior month, after verification and thresholds. October earnings therefore point to November 21–25 at earliest in the normal schedule. Docs list $20 PayPal/Wise and $100 other methods; [publishing terms §10.3](https://docs.apify.com/legal/store-publishing-terms-and-conditions) list $20 PayPal and $100 other methods. Treat Wise's threshold as unresolved; check the actual payout agreement. Below-threshold earnings roll forward. Do not buy usage to trigger payouts or count owner canaries as demand.

After publication, inspect independent paid usage weekly. Pause sales immediately on broken canaries, unclear source permission or misleading outcomes. After 14 public days with zero independent paid users, stop new Actor work and price experiments; leave only healthy listings/canaries. Change pricing only after buyer feedback or measured negative contribution, with owner approval and any Apify notice period. After two observed weeks above 10 owner support minutes/day, pause expansion.

## Store README selection

All four `actor.json` files omit `readme`. [Apify's definition reference](https://docs.apify.com/actors/development/actor-definition/actor-json) prefers `.actor/README.md`, then root `README.md`; this card supplies the preferred file and leaves developer instructions intact. Existing `store_listing.md` files are earlier drafts. These preferred READMEs govern the proposed Store text; Console deployment/publication remains a separate owner action.
