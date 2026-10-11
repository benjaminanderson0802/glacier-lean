# Permission-gated eBay sold research queries

These are exact query strings and filters for the approved research runner. **Do not run them through a scraper Actor unless eBay has first given express written permission for that automated access, or eBay confirms that the selected third-party tool is an approved access path.** The current [eBay User Agreement](https://www.ebay.com/help/policies/member-behavior-policies/user-agreement?id=4259) forbids robots, scrapers, and other automated access without eBay's prior express permission. Owner permission to use Apify does not by itself establish eBay permission. The Marketplace Insights API is also limited-release and requires eBay approval. This file is a queued research specification, not an instruction to bypass either restriction.

If permission is obtained, use only an Actor and account that eBay has specifically approved. Use `EBAY_US`, sold/completed results only, last 90 days, exact model/MPN when available, new and used conditions separated, results with best-offer sales excluded unless the actual accepted price is returned, and shipping shown separately from item price. Capture query, timestamp, item ID, condition, item price, shipping price, sold date, title, model/MPN, and source record. Do not collect seller personal information. Deduplicate item IDs. Calculate:

* observed sold count per query for the trailing 30, 60, and 90 days;
* a clearly labeled active-to-sold proxy using a separately permitted active-listing source and the same query/condition/date window;
* median total buyer price (item plus shipping), interquartile range, and matched model subset;
* supplier quote and current actual eBay fees separately, then contribution dollars and percentage.

No scrape or API result is included in this repo; therefore current sell-through, eBay competition counts, eBay median sold prices, and wholesale margin remain **uncertain — please check**.

| Rank | Search query (exact string) | Narrowing terms / why |
| --- | --- | --- |
| 1 | `72 inch skid steer grapple bucket` | Also run separate exact MPN/model queries; record freight and residential liftgate as distinct costs. |
| 1 | `78 inch skid steer land planer scarifiers` | Exact width/attachment/flow fit; separate new from used. |
| 1 | `6000 lb skid steer pallet forks 48 inch` | Exact capacity and fork length; exclude incompatible mini-loader frames. |
| 2 | `commercial 2 door reach in refrigerator restaurant` | Separate brand/model, voltage, fuel/refrigerant, freight and local pickup. |
| 2 | `commercial convection oven restaurant 208V` | Split by exact manufacturer/model/phase; do not combine installed service. |
| 2 | `commercial planetary mixer 60 quart` | Exact bowl capacity and voltage; count freight separately. |
| 3 | `Cummins C60D6 60kW generator A060A345` | Exact MPN/configuration; item only, exclude installation packages. |
| 3 | `Generac 60kW commercial generator 480V 3 phase` | Separate exact model, fuel and emissions variant. |
| 3 | `commercial automatic transfer switch 400 amp` | Separate amps, voltage, phase and compatible generator line. |
| 4 | `Kurt DX6 6 inch precision milling vise` | Exact maker/model; separate new, used, and vise-only/tooling-package results. |
| 4 | `Kurt DX8 8 inch precision milling vise` | Exact model; exclude jaw/accessory-only results. |
| 4 | `TMX 3-224-006 milling machine vise` | Exact model/MPN; use as a high-price control. |
| 5 | `MYCHWAY 8in1 Aristorm S Shape body contouring machine` | Exact model; record actual item price, condition, warranty and freight; exclude service bundles. |
| 5 | `MYCHWAY FC-23K5-US hydro dermabrasion machine` | Exact model; exclude treatment services and unrelated replacement parts. |

After permitted execution, save raw results and a reproducible summary under `research/evidence/` with the Actor name, version, permission reference, run date, input filters, output count, and any missing fields. Do not replace the unknown/uncertain labels above until that evidence is reviewed.
