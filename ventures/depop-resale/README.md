# Buy-first Depop resale preparation

This venture supports resale of **used clothing the owner personally buys and physically possesses before listing**. It does not source listings automatically or interact with Depop. Depop prohibits catalog drop-shipping and supplier/stock photos; the owner takes original photos of the exact item.

## What it prepares

- A research shortlist of five trend-led used-clothing categories, small-lot sourcing paths, and per-item buy ceilings.
- A local listing-prep command that reads a CSV of owner-verified item facts and original-photo paths, then writes a reviewable, vendor-neutral CSV with title, description, tags, size, condition, price, category, and photo paths.
- A local sold-item shipping checklist. It does not buy or generate labels.

The category order is a research hypothesis based on Depop's official trend coverage and used-lot availability, not measured sell-through or guaranteed sales. Price ceilings assume USD, 50% contribution margin after 3.3% + $0.45 US payment processing, seller-paid postage, and packaging. Each ceiling is the maximum all-in acquisition cost per sellable item, including that item's share of buyer's premium, inbound shipping, and purchase tax/fees. The estimate excludes owner labor, income taxes, boosting, returns, and other overhead. Check the current fee page and comparable sold prices before buying.

## Use

The fixture in `tests/fixtures/inventory.csv` documents the input columns. Supply your own private inventory CSV and photo folder; set `photo_origin` to `owner_original` only after taking the photos yourself.

```bash
~/w/glacier-lean/.venv/bin/python ventures/depop-resale/scripts/depop_prep.py listings \
  --input /path/to/your-inventory.csv \
  --photo-root /path/to/your-photos \
  --output /path/to/private/listing-handoff.csv
```

The script checks required item facts and photo files. It cannot verify photo provenance, authenticity, item legality, brand, or condition; the owner must inspect and approve every row. Do not include buyer personal information in the repository.

```bash
~/w/glacier-lean/.venv/bin/python ventures/depop-resale/scripts/depop_prep.py shipping \
  --item-id JKT-001 --buyer-name "Private order" --sold-at 2026-10-11 \
  --carrier USPS --output /path/to/private/shipping-checklist.md
```

## Crosslisting policy boundary

Depop's Terms of Service allow cross-listing platforms under conditions, and Depop's business help says it works with crosslisting tools through API connections. Depop's public materials reviewed for this build do **not** publish a list of approved vendor names or a CSV import contract. This venture therefore exports a neutral local handoff and does not label Vendoo, Crosslist, List Perfectly, or another vendor as approved. The owner must get Depop's confirmation that a particular provider is API-authorized and match that provider's documented import format before using it. Until then, use the CSV only as a review aid and list manually.

See [RESEARCH.md](RESEARCH.md) for dated source notes and [OWNER-STEPS.md](OWNER-STEPS.md) for the single owner workflow.

## Checks

```bash
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/depop-resale/tests
```

All scripts operate on local paths only. No Depop API, browser, scraping, buying, account, publishing, or shipping-label action is included.
