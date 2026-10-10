# DIBBS government supply

This venture prepares a source-linked bid sheet and quote files from public DLA DIBBS solicitation links and quotes you provide from an original manufacturer or its verified authorized distributor. It does not create accounts, contact suppliers, buy parts, sign certifications, or submit bids.

DIBBS's public page currently provides discovery links rather than a documented complete feed. A link alone does not establish that a solicitation is open to all suppliers, that a part is not electronic, or what fields the quote must contain. Check each linked solicitation and add its exact number, NSN, part number, due date, quantity, eligibility, required CSV fields and output filename to `$GLACIER_HOME/ventures/dibbs-supply/incoming/solicitations.json`. Add verified `quote_sources` (manufacturer/distributor type, email or HTTPS contact URL, on-file authorization document, and a supplier quote due date) to the solicitation record to prepare request drafts. Add returned supplier quotes and their authorization and traceability document paths to `quotes.json`. Missing or conflicting facts remain **uncertain — please check**. Closed, restricted, expired or electronic solicitations are excluded.

Run **Prepare DIBBS quote files** each day in Glacier. The command reads code from `$GLACIER_PROJECT_ROOT` when set, or the project at `$HOME/w/glacier-lean` by default; set the variable to your Glacier project directory if it is elsewhere. It refreshes the shared public feed, checks exact part and supplier matches, ranks supported quotes by gross margin, then prepares exact quote-request drafts for verified manufacturer/distributor contacts you supplied, and writes a bid sheet plus a separate CSV using each solicitation's required field order. The margin is `(unit bid price - unit cost) / unit bid price`; it does not include costs not present in the supplier quote. Quote files are drafts for your review. Traceability records must be on file before shipping.

The result vocabulary is **match**, **no match found in DLA DIBBS and supplier quotes as of [date]**, or **uncertain — please check**. A `match` means the supplied facts passed the script's checks; it is not a legal conclusion, award prediction, or government submission. The shared DIBBS feed reports its completeness and format alerts in the result.

## Your steps

1. Complete SAM.gov and CAGE registration yourself.
2. Review solicitations, request quotes only from original manufacturers or verified authorized distributors, provide quote evidence, and approve any parts spending.
3. Review each prepared bid, then personally sign and submit it in DIBBS. Keep traceability documents before shipping.

## Local input files

- `incoming/solicitations.json`: JSON array of verified solicitation details, including the exact official DIBBS detail URL with its solicitation number. Every `required_fields` entry must be supported by a script mapping (`solicitation_number`, `nsn`, `part_number`, `quantity`, `unit_price`, or `supplier_name`). `quote_file` must be a plain `.csv` filename.
- `incoming/quotes.json`: JSON array with solicitation/part number, supplier name and type (`manufacturer` or `authorized_distributor`), authorization and traceability evidence paths, quoted quantity, unit cost, and unit bid price.
- Quote requests are saved under `drafts/quote-request-drafts.json` with an exact recipient, subject, and prefilled message. Review the drafts at the approval step and send them manually; Glacier never contacts suppliers. Bid drafts are written under `drafts/`; no outbound action is performed. Keep customer or supplier documents local and delete them 30 days after the job closes unless retention is requested.

DIBBS, SAM.gov and CAGE accounts are owner steps. Glacier never enters credentials or submits anything to a government agency. No paid service is used.
