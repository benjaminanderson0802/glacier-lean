# Product Recall Checker (CPSC, NHTSA, FDA)

Check product names, barcodes, brands, models, and vehicle details against public CPSC, NHTSA, and FDA recall records. Get source links, per-source status, and dated results.

Check a product name, barcode, brand/model or vehicle make/model/year against public U.S. recall data. Get source-linked JSON for one item or a batch of up to 100, with explicit source status and a UTC check time.

## Use cases

- Triage inventory items for a reseller's manual recall review.
- Add dated recall-source checks to an internal product catalog.
- Route possible matches and source outages to a person before a product decision.

## Input example

```json
{
  "brand": "Fisher-Price",
  "product_name": "Rock 'n Play Sleeper"
}
```

Optional fields: `barcode`, `brand`, `model`, `product_name`, `year`. For vehicles, supply make in `brand`, vehicle `model` and integer `year` (1900–2100); otherwise NHTSA is skipped. Use `queries` for 1–100 item objects instead of a single top-level item. Names alone can produce uncertainty; an identifier is not proof of a unique product.

## Output example

Illustrative outage response for the input above. All applicable sources failed in this example, so no recall-check event is charged.

```json
{
  "outcome": "uncertain",
  "message": "uncertain — please check (CPSC, FDA-food, FDA-drug, FDA-device unavailable)",
  "query": {
    "brand": "Fisher-Price",
    "product_name": "Rock 'n Play"
  },
  "matches": [],
  "sources_checked": {
    "CPSC": {
      "status": "error",
      "as_of": "2026-10-11T02:00:00Z",
      "message": "Illustrative source timeout"
    },
    "FDA-food": {
      "status": "error",
      "as_of": "2026-10-11T02:00:00Z",
      "message": "Illustrative source timeout"
    },
    "FDA-drug": {
      "status": "error",
      "as_of": "2026-10-11T02:00:00Z",
      "message": "Illustrative source timeout"
    },
    "FDA-device": {
      "status": "error",
      "as_of": "2026-10-11T02:00:00Z",
      "message": "Illustrative source timeout"
    },
    "NHTSA": {
      "status": "skipped",
      "as_of": "2026-10-11T02:00:00Z",
      "message": "Vehicle make, model and year are required by this source."
    }
  },
  "checked_at": "2026-10-11T02:00:00Z"
}
```

Each query creates a dataset row with those six top-level fields. A match entry includes `source`, `recall_id`, `title`, `date`, `hazard`, `remedy` and `url`. Export JSON or CSV through Apify's dataset controls.

Outcomes: `match`, `no_match` (no match found in checked sources as of the shown date), or `uncertain` (limited input, a possible match, or source failure). Any source error makes the overall outcome uncertain, even if candidate matches are returned. Review `sources_checked` and the official notices; an empty match list is not a safety assurance.

## Pricing

The `recall-check` event costs **$0.01 per input query**, with platform usage included. A readable no-match or uncertain result is charged when at least one source responded, including partial results when another source failed. A result with only source outages is free. Billing is per input item, not per recall returned.

The maximum event charge per run is **$1.00** for 100 input queries. For a smaller batch, choose a lower run cap if desired. Each new run can incur new event charges.

## Sources, limitations and legal notes

Uses [CPSC recall data](https://www.saferproducts.gov/RestWebServices/Recall?format=json), [NHTSA vehicle recalls](https://www.nhtsa.gov/nhtsa-datasets-and-apis), and openFDA [food](https://open.fda.gov/apis/food/enforcement/), [drug](https://open.fda.gov/apis/drug/enforcement/) and [device](https://open.fda.gov/apis/device/enforcement/) enforcement data. FSIS is not covered. This is not a VIN lookup, complete historical recall archive, or UPC catalog.

Matching depends on identifiers present in official records. Missing identifiers, bounded source searches and delayed data can miss a relevant notice. There is no published 1,000-item accuracy benchmark for this release; do not infer a measured accuracy rate from a successful example. No statement that a product is safe, legal to sell or cleared for use is made. The tool is independent of the agencies and does not replace checking the official recall notice or professional advice.

Use only authorized inputs. Requests must respect source terms and rate limits. For technical issues, share a non-sensitive query and run ID in Apify Issues, never a token or private inventory file.
