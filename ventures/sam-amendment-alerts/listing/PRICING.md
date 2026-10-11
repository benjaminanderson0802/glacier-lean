# Price recommendation and competitor evidence

## Recommendation

Start at **$0.001 per verified change event** (USD $1 per 1,000 changed notice rows), with no start fee and no charge for a baseline, no-change result, uncertain result, incomplete API response, or outage. One event represents one successfully written new-notice, amendment/version-change, or response-deadline-change row. It does not represent a bid or eligibility judgment. This is a proposed launch price; willingness-to-pay has not been tested.

## Apify Store comparison (checked 2026-10-11)

| Store listing | Displayed price | Difference from this Actor |
| --- | ---: | --- |
| [SAM.gov Opportunities Scraper — Federal Solicitations](https://apify.com/maydit/sam-gov-opportunities-scraper/api/openapi) | From $1.20 per 1,000 results | General opportunity retrieval; this Actor proposes $1.00 per 1,000 actual changes and charges nothing when there is no observed change. |
| [SAM.gov Contract Opportunities Scraper](https://apify.com/acquistion-automation/sam-gov-contracts-scraper/api/openapi) | From $2.82 per 1,000 results | General opportunity scraping; this Actor is a narrower change monitor and proposes a lower event price. |
| [SAM.gov Scraper: Federal Contract Opportunities](https://apify.com/agentready/sam-gov-opportunities/api/openapi) | From $1.52 per 1,000 opportunities | General search and notice output; this Actor bills only verified changes between complete snapshots. |

Prices are public Store observations from the check date and may change. Their result units and features are not identical, so this is directional evidence only. The recommendation prioritizes low cost and only billing on detected changes, not a claim of superior coverage.

## Console settings

Set the `opportunity-change` custom event to USD $0.001 and mark it primary. Disable automatic `apify-actor-start` and `apify-default-dataset-item` events. The code charges after `push_data` returns and skips baseline/no-change/uncertain rows. Confirm platform usage inclusion and a maximum charge before the owner approves publication.
