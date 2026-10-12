# Independent venture review — R3

Read against `ventures/SPEC.md` in the PH12.22 review checkout after locally merging B1 (already in the base) and the four venture branches. No implementation files were changed.

## Property tax appeals (`property-tax`)

| Spec field | Finding |
|---|---|
| Purpose | **partial** — Cook County packet prep only; no appeal filing or actual public-record prospecting ([README](property-tax/README.md), [property_tax.py](property-tax/scripts/property_tax.py:48)). |
| Inputs | **partial** — consumes customer notice and comparable documents, but public roll omits mailing address and assessed value; owner/customer must provide records ([README](property-tax/README.md), [PROOF](property-tax/PROOF.md)). |
| Outputs | **partial** — packet and local postcard proof only; no appeal filing or decision tracking evidenced ([flows](property-tax/flows/)). |
| Blocks | **partial** — feeds, reader, mail, deadlines, customer are declared; portal filer is not used ([venture.json](property-tax/venture.json)). |
| Loop | **partial** — daily roll refresh is scheduled; customer acquisition, packet delivery, appeal handoff and outcome tracking remain manual ([venture.json](property-tax/venture.json), [refresh flow](property-tax/flows/property-tax-refresh-roll.json)). |
| Checks | **partial** — packet requires three recent source-linked sales and customer arm’s-length confirmation; no live comparables or full-roll check ([property_tax.py](property-tax/scripts/property_tax.py:98), [PROOF](property-tax/PROOF.md)). |
| Approval gates | **partial** — packet/postcard review is gated; county-rule conflict and Texas registration remain owner decisions ([venture.json](property-tax/venture.json), [packet flow](property-tax/flows/property-tax-prepare-packet.json)). |
| Billing | **partial** — only a flat packet fee may be enabled after owner confirmation; spec’s contingency option is disabled ([venture.json](property-tax/venture.json)). |
| Edge cases | **partial** — uncertain/incomplete records stop packet readiness and hearing cases are packet-only; stale/full-feed failure still blocks use ([property_tax.py](property-tax/scripts/property_tax.py), [PROOF](property-tax/PROOF.md)). |

**Live source:** Cook County Socrata one-row request returned **1 record**, PIN `01011000020000`, tax year 2025, no schema issue (one-row query, not a roll count). The script’s full feed sync was still downloading after 60 seconds and was stopped; prior proof also records a full-roll timeout. No real notice or comparable-sales packet was available.

**Tests:** `cd ventures/property-tax && /home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests` — **6 passed**.

**Owner steps:** 3, each with instruction. Step 1 links to Cook County rules and residential appeals; step 2 links TDLR but is Texas-only and not needed for the Cook County launch; step 3 lacks a direct link to the exact mailing approval screen/artifact. Important unresolved discrepancy is surfaced in the manifest: spec says Cook County needs an attorney; linked Assessor rules say a party may file without one. No hidden automatic filing or mailing found; both remain customer/owner actions.

**Prioritized fixes:**

1. `ventures/blocks/feeds/core.py::_sync_socrata_stream` — support a bounded latest-year/current-roll sync or paged continuation with visible progress; the full-source download stalls and cannot support the scheduled venture refresh.
2. `ventures/property-tax/venture.json::your_steps[0]` — keep launch disabled until the owner resolves the spec/Assessor representation-rule discrepancy; do not encode either legal interpretation as settled.
3. `ventures/property-tax/README.md::Your steps` — link the exact approval artifact and remove or label the unrelated Texas step for the Cook County launch path.

## Utility audits (`utility-audits`)

| Spec field | Finding |
|---|---|
| Purpose | **partial** — narrowed to Indiana restaurant electricity exemption; source asks to start with a clear-rule state but does not select Indiana ([README](utility-audits/README.md)). |
| Inputs | **partial** — customer-entered annual statewide sales, 12 months of meter figures/bills and optional rates; no UtilityAPI, Arcadia, Green Button, PDF reader or automatic rate lookup ([README](utility-audits/README.md), [utility_audit.py](utility-audits/scripts/utility_audit.py)). |
| Outputs | **partial** — unsigned ST-200R field data and estimate; it does not fill a refund form or create DOR’s ST-109R ([README](utility-audits/README.md)). |
| Blocks | **missing** — spec lists no specific blocks; implementation declares none ([venture.json](utility-audits/venture.json)). |
| Loop | **missing** — no recurring or end-to-end running loop is specified or implemented; one calculator flow only ([venture.json](utility-audits/venture.json)). |
| Checks | **partial** — validates threshold, consecutive months, and draft unsigned state; rate links/availability and full tariff are not checked ([PROOF](utility-audits/PROOF.md), [utility_audit.py](utility-audits/scripts/utility_audit.py)). |
| Approval gates | **done** — owner state confirmation and draft review gates are present; customer signs/submits ([flow](utility-audits/flows/utility-audit-calculator.json)). |
| Billing | **partial** — share-of-savings model is only a proposal and requires owner approval; no billing is implemented ([venture.json](utility-audits/venture.json)). |
| Edge cases | **missing** — no spec edge cases are stated; implementation reports missing/invalid data as uncertain but has no recovery workflow ([utility_audit.py](utility-audits/scripts/utility_audit.py)). |

**Live source:** three linked Indiana DOR references responded HTTP 200 (utility sales-tax page, Bulletin #11 PDF, Bulletin #29 PDF). The script does not fetch these sources. **0** real utility bills or rate plans were fetched/validated; no customer records were available, so real-data calculator count is **0**. Proof fixtures are synthetic.

**Tests:** `cd ventures/utility-audits && /home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests` — **7 passed**.

**Owner steps:** 3, but none of the three steps themselves gives an exact link. README points to PROOF for sources; add the direct ST-200R and DOR rule links to the first confirmation/review instruction. User-entered external tariff links are not validated. Billing share is not automated, correctly remains behind owner approval; clarify that state filing is customer-signed and submitted.

**Prioritized fixes:**

1. `ventures/utility-audits/scripts/utility_audit.py::_rate_check` — fetch or validate official rate source URLs and label unsupported charges/availability; current inputs can look like a rate audit without checking the tariff.
2. `ventures/utility-audits/venture.json::your_steps` — add exact DOR rule and ST-200R links beside the owner/customer instructions.
3. `ventures/utility-audits/venture.json::product.billing` — keep share billing disabled until owner records the approved model and its legal basis; current owner gate is prose only.

## DIBBS government supply (`dibbs-supply`)

| Spec field | Finding |
|---|---|
| Purpose | **partial** — bid preparation is present but live DIBBS feed currently supplies no solicitation records ([README](dibbs-supply/README.md), [dibbs_supply.py](dibbs-supply/scripts/dibbs_supply.py:277)). |
| Inputs | **partial** — solicitors/quotes are owner-supplied and exact-match checked; source does not provide usable data at present ([README](dibbs-supply/README.md)). |
| Outputs | **partial** — ranked sheet and solicitation CSV drafts are generated only from verified local inputs; no live bid example ([dibbs_supply.py](dibbs-supply/scripts/dibbs_supply.py:120)). |
| Blocks | **partial** — only shared feeds are declared ([venture.json](dibbs-supply/venture.json)). |
| Loop | **partial** — daily schedule exists, but daily work still requires owner to verify every solicitation and obtain quotes ([venture.json](dibbs-supply/venture.json), [README](dibbs-supply/README.md)). |
| Checks | **partial** — exact part/supplier, eligibility, quote, margin and traceability checks exist; no live solicitation reached them ([dibbs_supply.py](dibbs-supply/scripts/dibbs_supply.py:52)). |
| Approval gates | **partial** — owner registration and bid signature are explicit; parts spending is an owner instruction, not a flow approval gate ([flows](dibbs-supply/flows/), [README](dibbs-supply/README.md)). |
| Billing | **done** — none; venture manifest says no customer billing/customer layer is needed ([venture.json](dibbs-supply/venture.json)). |
| Edge cases | **partial** — closed/uncertain/restricted and electronic parts are handled, but the feed warning page results in no usable records ([dibbs_supply.py](dibbs-supply/scripts/dibbs_supply.py), [PROOF](dibbs-supply/PROOF.md)). |

**Live source:** one public sync of `dla_dibbs` returned **0 rows**, `changed: false`, alert `ValueError: source returned no records; existing snapshot retained`. DIBBS redirects to its DoD warning/consent page; no consent or login attempted. No other public source is used for solicitation discovery.

**Tests:** `PYTHONPATH=/tmp/gf-R3-review /home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/dibbs-supply/tests` — **11 passed**. From the venture directory without `PYTHONPATH`, 10 passed and one test could not import `ventures`; this is a test invocation/package-root issue, not a behavior failure.

**Owner steps:** 3; step 1 and 2 lack exact links in README/manifest, although the registration flow includes SAM.gov and CAGE links. Put those exact links and DIBBS solicitation search link in the visible owner steps. Quote contact is manual, and parts spending/each bid submission are rightly owner actions; no automated supplier contact or bidding found.

**Prioritized fixes:**

1. `ventures/blocks/feeds/core.py::_sync_dibbs_html` — handle the public warning/consent redirect as a documented unavailable source and provide an owner-entered official-link intake path; current scheduled feed repeatedly yields zero rows.
2. `ventures/dibbs-supply/venture.json::your_steps` — add exact SAM.gov, CAGE and public solicitation links so the three steps can be completed without searching.
3. `ventures/dibbs-supply/flows/dibbs-daily-prep.json` — add an explicit approval node before any parts purchase/commitment; current spending rule is only described in prose.

## Carpenter’s goods (`carpenter-goods`)

| Spec field | Finding |
|---|---|
| Purpose | **done** — creates listing drafts for the owner’s shop ([README](carpenter-goods/README.md), [listing_prep.py](carpenter-goods/scripts/listing_prep.py:14)). |
| Inputs | **partial** — maker facts/photos, three source-linked completed sales, and owner exports are required; every input is manual ([README](carpenter-goods/README.md)). |
| Outputs | **done** — Etsy/Shopify drafts and paid-sale commission calculation; no publishing or money movement ([listing_prep.py](carpenter-goods/scripts/listing_prep.py:38)). |
| Blocks | **done** — none used or specified for this venture; no platform write connector ([venture.json](carpenter-goods/venture.json)). |
| Loop | **partial** — listing drafts and commission summaries only; “run his Etsy shop,” Shopify site and routine buyer answers are not automated ([SPEC](SPEC.md), [README](carpenter-goods/README.md)). |
| Checks | **partial** — same-category completed sale rows and median price; does not fetch/check current market sales or verify source content ([listing_prep.py](carpenter-goods/scripts/listing_prep.py:17)). |
| Approval gates | **partial** — first listing requires review before manual publish; the manifest does not gate ongoing listing publication beyond manual handling ([venture.json](carpenter-goods/venture.json), [flow](carpenter-goods/flows/carpenter-prepare-listing.json)). |
| Billing | **partial** — calculates commission from owner export and written rate but does not invoice/collect ([listing_prep.py](carpenter-goods/scripts/listing_prep.py:66)). |
| Edge cases | **partial** — Facebook Marketplace is manual only; missing comparables becomes uncertain; other operating/support cases are not defined ([README](carpenter-goods/README.md), [listing_prep.py](carpenter-goods/scripts/listing_prep.py:21)). |

**Live source:** **0** live comparable sales and **0** live paid orders. The script intentionally does not scrape Etsy or Shopify; source rows and sales exports must come from the owner. No Etsy/Shopify live listing or shop data was accessed.

**Tests:** `cd ventures/carpenter-goods && /home/glacier/w/glacier-lean/.venv/bin/python -m unittest discover -s tests -v` — **4 passed**.

**Owner steps:** 3, with instructions, but no step has an exact link to Etsy or Shopify. The inputs and 30-day retention duty are documented; supply those exact shop/platform links. Manual publishing after approval is appropriately gated. No automated external messaging or payment was found.

**Prioritized fixes:**

1. `ventures/carpenter-goods/README.md::Running loop` — state that routine buyer replies and operating the shops remain entirely manual, or implement them behind owner approval; current implementation only drafts listings.
2. `ventures/carpenter-goods/venture.json::your_steps` — add exact shop/platform links and a direct input/export instruction for the maker.
3. `ventures/carpenter-goods/scripts/listing_prep.py::prepare_listing` — verify completed sale evidence freshness and reject duplicate/invalid source rows before using the median.

## Fixed

### Property tax appeals (`property-tax`)

1. **Cook County feed progress** — Shared-feed fix committed separately as `5dacc86` (`Resume county feed sync and surface DIBBS access limits`). Latest-year sync now resumes in 10,000-row pages, limits each invocation to five pages, exposes downloaded/total/tax-year progress, and does not replace the previous complete snapshot until the new roll is complete. Live source run on 2026-10-10 found tax year 2026 with **1,864,270** rows; this invocation staged **50,000**, reported continuation offset 50,000, and kept the prior snapshot active. Full sync remains in progress.
2. **County representation discrepancy** — Cook County launch remains disabled until the owner resolves the spec/Assessor difference and confirms the packet-only county scope. No legal interpretation was selected.
3. **Owner steps and approval artifact** — The Texas registration step is labeled a future expansion, outside Cook County launch. The mailing step names the `approve_proof` step and exact local postcard proof/review directories; README links directly to the Assessor rules and residential instructions.

Test: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/property-tax/tests` — **6 passed**. Shared feed tests: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/feeds/tests/test_feeds.py` — **11 passed**.

### Utility audits (`utility-audits`)

1. **Rate source handling** — The calculator checks supplied rate links for HTTPS reachability and same-host redirects. It rejects malformed links and loopback/private literal addresses before fetching. It labels reachable links `reachable_unverified`, keeps availability uncertain, and states that official source identity and full tariff terms are not independently confirmed. Invalid or unavailable links yield `uncertain — please check` with no savings estimate.
2. **Owner steps** — Added direct Indiana DOR utility exemption, Bulletin #11, Bulletin #29 Appendix B, and ST-200R form links. The customer-signs-and-submits direction remains explicit.
3. **Billing gate** — Share billing is disabled until the owner records approval of both the model and its legal basis. No legal or billing model decision was made.

Test: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/utility-audits/tests` — **9 passed**. Rate-source HTTP responses were mocked; no real utility tariffs or customer bills were available.

### DIBBS government supply (`dibbs-supply`)

1. **Warning/consent source** — The shared adapter now reports the DoD warning/consent redirect as unavailable, makes no acknowledgement or login attempt, and directs the owner to verify the official solicitation and enter its exact link/details into local `solicitations.json`. Live `dla_dibbs` sync on 2026-10-10 returned **0 rows**, `changed: false`, and the specific warning/consent alert.
2. **Owner steps** — Added exact SAM.gov entity registration, CAGE, and DIBBS solicitation-search links.
3. **Parts commitment gate** — Added a distinct Glacier approval node for the exact supplier, part, quantity, terms, and spend before purchase. The decline branch records that no purchase was made. Glacier does not place orders.

Test: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/dibbs-supply/tests` — **11 passed**. No solicitation was available from the public feed; no bid or purchase occurred.

### Carpenter's goods (`carpenter-goods`)

1. **Manual operating loop** — README now states that buyer replies, order handling, customer support, inventory updates, and future listing publication remain manual.
2. **Owner steps** — Added direct Etsy shop-dashboard and Shopify admin links, plus the `product.json`, `comparables.json`, and `paid-sales.json` input/export instructions.
3. **Comparable validation** — Pricing now requires completed-sale dates within the prior 365 days and excludes/reports duplicate source URLs, invalid values/dates, future/stale sales, incomplete records, and category mismatches before calculating the median.

Test: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/carpenter-goods/tests` — **6 passed**. Fixture records are synthetic; no live market sales or shop exports were available.
