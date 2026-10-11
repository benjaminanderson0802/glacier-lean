# Price recommendation and competitor evidence

## Recommendation

Start at **$0.001 per verified exact match**, with no start fee and no charge for a no-match, stale/uncertain row, or unavailable file. A 100-query run has a maximum of $0.10 in custom event charges. This is a proposed launch price, not validated willingness-to-pay. Keep Apify's platform-usage inclusion and customer run cap visible in the Store pricing panel.

The Actor only compares a buyer-authorized, dated CSV uploaded by the buyer. It does not download or resell an Alabama roster, so it offers narrower coverage than live multi-state verifiers. That narrower scope supports a lower event price and makes the input/source limitation explicit.

## Apify Store comparison (checked 2026-10-11)

| Store listing | Displayed price | Difference from this Actor |
| --- | ---: | --- |
| [Virginia Contractor License Lookup (DPOR Bulk)](https://apify.com/muhammadafzal/virginia-contractor-license-lookup) | $0.005 per contractor record, plus a $0.005 start event | A live Virginia database lookup; proposed Alabama event is 5× lower and has no start fee, but requires the user to supply the roster. |
| [US License Verification (Contractors & Professionals)](https://apify.com/maki-dev/us-license-verify) | From $30 per 1,000 results ($0.03 each) | Live normalized searches across 11 states; materially broader than this single-state uploaded-file checker. |

These are public Store prices observed on the check date and can change. They are price anchors, not proof of identical coverage or cost. The proposed $0.001 price prioritizes trial and repeat use; review actual settled event and platform costs before changing it.

## Console settings

Use the custom `license-lookup` event at USD $0.001, mark it primary, and disable automatic Actor-start and dataset-item events. The Actor calls the custom charge only after the dataset write succeeds and only for a verified `match`. A failed charge/run can be retried with the run's idempotency key. Never bill no-match or uncertain results.
