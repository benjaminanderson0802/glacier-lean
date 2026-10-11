# Amazon FBA fee variance digest

This small local tool compares FBA fulfillment-fee lines in a seller's own Amazon Settlement Report V2 with that seller's expected per-unit fee by SKU and size tier. It highlights fee differences, estimates expected versus observed per-unit margin when the report includes the sale line, and links each result to the original report row.

It does not access Amazon accounts, estimate the official fee schedule, find competitor data, submit disputes, or promise a refund. The seller supplies the current fee expectation and unit cost. Commission, storage, inbound placement, taxes, refunds, and other costs are outside this first version, so its margin figure is only a narrow estimate for human review.

## Who pays and price hypothesis

Small Amazon FBA sellers with enough SKUs or settlements that a quick manual reconciliation is inconvenient are the intended buyers. The initial price hypothesis is **$49 for one one-time pilot digest** covering one settlement report and one expected-fee CSV. This is not validated willingness-to-pay evidence; the paid-pilot pitch in [PILOT.md](PILOT.md) is meant to test it before expanding the product.

## Run it locally

Use an Amazon **Settlement Report V2 flat file** downloaded by the seller from Seller Central. It is tab-delimited. The seller also prepares an expected fee CSV with these columns:

```csv
sku,size_tier,expected_fee_usd_per_unit,unit_cost_usd
MUG-12OZ,Large standard-size,5.00,12.00
```

Run:

```sh
~/w/glacier-lean/.venv/bin/python ventures/fba-fee-check/scripts/fee_digest.py \
  /path/to/settlement-v2.tsv \
  /path/to/expected-fees.csv \
  /path/to/fee-digest.csv
```

The pilot accepts USD only and fails closed on missing required columns, unsupported currencies, and ambiguous comma-formatted amounts. Reports and outputs stay on the machine where the command runs. Review the CSV's source order, item code, and report row in Seller Central before taking any action.

The parser follows Amazon's documented Settlement Report V2 column names, including `amount-type`, `amount-description`, `amount`, `fulfillment-id`, `sku`, and `quantity-purchased`. Amazon documents the report as a tab-delimited flat file and says V2's general-purpose amount columns categorize fees; see [Settlement Reports — Flat File V2](https://developer-docs.amazon.com/sp-api/docs/report-type-values-settlement#flat-file-v2-settlement-report). Amazon says its fee estimates are not guaranteed in its [fee-estimate documentation](https://developer-docs.amazon.com/sp-api/docs/notification-type-values); a seller's own current report and fee schedule remain authoritative for this comparison.

## Owner steps

The one first step is sending the manually prepared business pitch in [PILOT.md](PILOT.md). If a prospect accepts, ask them to download and provide their own report and fee schedule. Run the command above locally and return the digest for the seller to review. Never ask for a password, reuse a Seller Central login, scrape a marketplace, or send data to an outside service.

## Source and legal/terms cautions

- This CSV-only pilot does not use SP-API. Any later account connection would require seller authorization and the applicable Amazon developer/app registration route described in the reseller research.
- Use only reports downloaded and supplied by the seller. Do not scrape Amazon pages or another seller's data.
- Amazon fee estimates can change and are not guaranteed. A variance is a prompt to investigate, not proof of an error, recoverable money, or a right to reimbursement.
- Outreach is manual only. No list harvesting or automated email. Honor opt-outs and include accurate sender information and a postal address on a commercial pitch.
- Customer files are sensitive business data. The pilot keeps them local; delete copies when the seller's job is closed unless retention is agreed.

## Files

- `scripts/fee_digest.py` — local command-line prototype.
- `tests/fixtures/` — seller-shaped synthetic Settlement V2 and fee schedule data.
- `tests/test_fee_digest.py` — fixture-based acceptance tests.
- `samples/sample-fee-digest.csv` — one example output from those fixtures; not live seller data.
- `prospects.csv` — candidate businesses sourced from Amazon's official seller story directory pages. They are leads to qualify, not confirmed buyers; verify current FBA use before pitching.
