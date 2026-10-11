> Copy of the owner's doc "Venture Portfolio and Features" (Venture Build Spec), 2026-10-10. This is the source of truth for ventures; it overrides the older per-venture specs.


Venture Build Spec
 · Benjamin Anderson
This spec is for the AI agents that build and run fourteen automated ventures on Glacier. Each venture is a legitimate business that prepares paperwork, checks public data or files claims customers are already owed, with the customer signing and submitting anything that goes to a government agency. Read the rules and building blocks first; every venture spec below refers to them.
How to use this spec
Read **Rules for every venture** and **Shared building blocks** before starting any venture. They apply everywhere and are not repeated in the venture specs.
Build in the order of the **Build queue**. Build each shared block for the first venture that needs it; generalize it only when a second venture uses it.
For each venture, work through its spec fields in order: purpose, customers and channel, inputs, outputs, blocks used, running loop, checks, approval gates, billing, edge cases.
Keep one builder per area at a time. A shared block has a single owner; other workers read it but do not edit it.
Write progress to the venture's progress file after every task, and rewrite it rather than appending.
**A venture is done when:** it is live, a first customer has paid, and every check in its spec passes on real data. Then move to the next item in the queue. Polish comes later, only if numbers justify it.
**A task is done when:** its stated check passes, verified by a separate evaluator that did not build it. Claiming done without the check output is not done.
**When blocked:** write a blocker report with the exact error, the command or page involved, and two alternatives already tried. Send it to the supervisor. Escalate to the owner only for money, legal questions, account sign-ups or identity verification.
**When a safety concern comes up:** check the venture's purpose and the rules below first; most concerns come from missing context. If the concern still holds (a site's terms ban automation, a step needs a license), redesign that step and record the change here so no later worker trips on it.
Rules for every venture
These hold for every venture and every agent. Write them into each venture's system prompt.
**Output vocabulary.** Every result a customer sees is one of: "match", "no match found in [sources] as of [date]", or "uncertain — please check". Legal conclusions such as safe, compliant or exempt are the customer's call; present a checklist they confirm instead.
**Two-engine agreement.** A model's extracted or judged value counts only when a script check or a second engine agrees. Disagreement becomes "uncertain" and goes to the customer to confirm.
**Filing.** The customer (or their licensed broker) certifies and submits anything going to CBP, CPSC, FDA or OSHA. Agents prepare files and, where a portal allows a delegate, submit under the customer's own account with their e-signed authorization.
**Money with partners.** Customs brokers and law firms pay us flat fees only. Commissions on refunds or brokerage fees stay out of every deal, as do fee splits with attorneys. Unclaimed-property and finder rules vary by state; check before any contingency deal.
**Outreach.** Customers come from marketplaces, partner portals, search pages and postcards. Postcards show a clear sender and never resemble a government notice; every do-not-mail request is honored within one run. Texts go only to people who opted in. Reviews come only from real customers, and every community post is made by a disclosed, human-owned account.
**Volume over rescue.** A prospect who won't buy through the self-serve path is skipped. A single stuck case gets one automatic retry, then is dropped, refunded or rolled forward. Human time goes only to problems that affect many customers at once.
**Platform terms.** Use official APIs and approved integrations first. Use browser automation only where the site's terms allow it and the customer has granted access. Never scrape logged-in consumer platforms (Facebook Marketplace, LinkedIn) or load boards.
**Approval gates (owner only).** Anything that spends money, signs up for an account, verifies identity, publishes a new product listing for the first time, or answers a legal question. Everything else runs without asking.
**Data handling.** Customer uploads are deleted 30 days after the job closes unless the customer opts to keep them. Portal credentials are stored encrypted and used only for that customer's job.
Shared building blocks
Eight blocks serve all fourteen ventures. Each has one owner, its own test set, and a check that must pass before any change goes live.
| Block |
Input |
Output |
Check before release |
Used by
| Document reader |
PDF, photo or CSV |
Structured fields, each with its source page and a confidence flag |
95%+ field agreement between two engines on a labeled sample set; disagreements marked uncertain |
CPSC, FDA, freight, warranty, tariff, utility, property tax, co-op
| Rules checker |
Fields plus an official rule set |
Pass, fail or uncertain, with the rule cited |
Accepts every known-good sample, rejects every hand-made bad one |
CPSC, FDA, OSHA, tariff, warranty, recall
| Portal filer |
Customer authorization, credentials, fields |
Submitted form plus saved confirmation (PDF or screenshot) |
Test submission succeeds; confirmation saved; repeat run doesn't double-file |
Warranty, co-op, OSHA, property tax, freight, DIBBS prep
| Government data feed |
Source list (CPSC, NHTSA, FDA, FSIS, OSHA, county rolls, DLA, state boards) |
Clean, dated records in one database |
Row counts within 1% of each source's totals; known canary records still parse; alert on any format change |
Recall, Apify tools, OSHA, property tax, CPSC codes, DIBBS
| Deadline tracker |
Start date plus rule (60/90 days, 30/120 days, Jan 2–Mar 2) |
Reminders and "due soon" flags |
Test items fire on the right dates, once each |
Warranty, freight, OSHA, FDA, tariff, property tax, co-op
| Customer layer |
Signup |
Account, Stripe billing, e-signature, status page, support inbox |
Test purchase, refund and e-sign complete end to end |
All except DIBBS
| Acquisition engines |
Public lists, marketplace listings, unique data |
Postcards (via Lob), store listings, one page per data object |
Every page carries real, distinct data; every postcard passes address verification and the outreach rules |
All
| Platform connectors |
OAuth or API access |
Jobs, shipments, products read from Jobber, ShipStation, Shopify, Apify, Chrome extension |
Connects to a test account; read-only unless the venture needs writes |
Warranty, co-op, OSHA, postcards, freight, FDA, CPSC, recall, Apify
**Model use.** Scripts first, then the local model for short labels and first-pass extraction, then the subscription model for cross-checks, messy documents, code and judging. Computer use only where there is no API or download.
Build queue
Work the queue top to bottom. Items marked parallel run alongside the item above them. Start every approval wait in the right-hand column as soon as the item begins, so reviews finish while building continues.
| Order |
Venture |
Blocks it builds or reuses |
Start early (approval waits) |
Timing reason
| 1 |
CPSC data prep |
Builds reader, rules checker, data feed, customer layer |
Trade lawyer opinion on flat-fee broker model |
Mandatory since July 8, 2026; second wave Jan 8, 2027
| 1 (parallel) |
Apify data tools |
Reuses data feed |
Apify developer account and payout |
Fastest revenue
| 2 |
Warranty registration |
Adds portal filer, deadline tracker, Jobber connector |
Jobber developer account; app review after 5 accounts |
Flagship of bundle 1
| 3 |
Recall checker |
Reuses data feed; adds matching |
Chrome Web Store review |
Long store review
| 4 |
Co-op claims + street postcards |
Reuses portal filer, Jobber; adds mail engine |
Lob account; printer with post office drop |
Dealer year-end budgets in November
| 5 |
Freight claims |
Reuses reader, deadlines; adds ShipStation connector |
ShipStation partner access |
New LTL shippers arriving now
| 6 |
FDA cosmetics tool |
Reuses reader, rules checker; adds Shopify connector |
Shopify Partner account and app review |
Review takes weeks
| 7 |
OSHA filing |
Reuses mail engine, portal filer |
None |
Hard window Jan 2 – Mar 2
| 8 |
Property tax appeals |
Reuses mail, reader, portal filer |
Texas consultant registration if filing in Texas |
County notice seasons
| 9 |
Utility audits, DIBBS, carpenter's goods |
Mostly reuse |
DIBBS: SAM.gov and CAGE registration |
Fill free worker time
| Hold |
Tariff estimator |
Reuses reader, deadlines |
Lawyer must approve first |
Window closing; build only if approved
Venture index
Index of all fourteen ventures. Prices are starting estimates; adjust from real conversion data.
| Venture |
Bundle |
How customers find it |
Price (est.) |
Status
| Warranty registration |
Contractor back office |
Jobber app |
$49–149 per shop/mo |
Flagship
| Co-op claims |
Contractor back office |
Inside the Jobber app |
15–25% of recovered funds |
Folded into bundle
| Street postcards |
Contractor back office |
Each card advertises the next |
~$550 per ad spot |
Keep
| OSHA filing |
Contractor back office |
January mail + Jobber |
$49–199 per site/yr |
Folded into bundle
| CPSC data prep |
Import compliance desk |
Customs broker portal |
Flat monthly fee to brokers; $19–49 per batch direct |
Top opening
| Freight claims |
Import compliance desk |
ShipStation app |
20–30% of recovery |
New opening
| Tariff estimator |
Import compliance desk |
Broker and law-firm tool |
Flat fee |
Reshaped, time-boxed
| Recall checker |
Government data layer |
Chrome store + recall pages |
$5–9/mo individuals, $29–79/mo stores, API usage |
Keep
| Apify data tools |
Government data layer |
Apify Store + agent directories |
Per use |
Keep
| Property tax appeals |
Public records to mail |
Tax-notice postcards |
Share of savings or flat packet fee |
Keep
| FDA cosmetics tool |
Standalone |
Shopify App Store |
Subscription |
Keep
| DIBBS supply |
Standalone |
Agency posts the orders |
Margin on parts |
Keep
| Utility audits |
Standalone |
One-state calculator |
Share of refunds |
Narrowed
| Carpenter's goods |
Standalone |
Etsy search |
Commission |
Side project
Spec: Warranty registration
**Purpose.** HVAC brands only honor their longer parts warranty if each new unit is registered online within a set window: 60 days for Trane, Goodman, Daikin and Lennox, 90 for Carrier. Missing it usually cuts parts coverage from 10 years to 5. We register every install for the contractor, with their authorization, so homeowners keep full coverage.
**Customers and channel.** HVAC and home-services contractors, found through the Jobber app marketplace first, then Housecall Pro and ServiceTitan. Each homeowner certificate also advertises the service.
**Inputs.** Completed install jobs from Jobber; a data-plate photo (model and serial) texted or uploaded by the technician; homeowner name and address from the job; the contractor's brand portal credentials or dealer number.
**Outputs.** A registration confirmation saved per unit; a branded certificate emailed to the homeowner with the contractor's logo and a small "registered by" footer; a dashboard of every unit and its deadline.
**Blocks used.** Platform connector (Jobber), document reader, portal filer, deadline tracker, customer layer.
**Running loop.**
Pull newly completed install jobs from Jobber every hour.
Request the data-plate photo by text if it's missing (technician opted in at signup).
Read model and serial; confirm with the second engine and the brand's serial format.
Skip units in regions where registration isn't required (California, Quebec, and Florida and Georgia for Lennox units installed on or after January 1, 2026).
Register on the brand portal and save the confirmation.
Email the homeowner certificate.
Flag any unit within 10 days of its deadline that isn't registered.
**Checks.** Model and serial pass both engines and the brand's format; a confirmation file exists for every registered unit; no unit is registered twice.
**Approval gates.** First Jobber marketplace listing; first 20 homeowner emails reviewed by the owner.
**Billing.** $49–149 per shop per month by install volume, through Stripe or Jobber's billing.
**Edge cases.** Unreadable photo: one automatic retake request, then mark skipped and tell the contractor. Portal change breaks submissions: pause that brand, alert the owner, keep other brands running.
**Done when.** Live in Jobber, one paying shop, and every check passing on real installs.
Spec: Co-op claims and street postcards
These two run together: postcards are the ads, and co-op claims get brands to repay dealers for them.
Co-op claims
**Purpose.** National brands set aside co-op money (typically 1–5% of a dealer's purchases) to repay local ads featuring the brand. It expires if not claimed with proof. We file claims for dealers who authorize us.
**Customers and channel.** Brand dealers among the warranty app's contractors (offered inside the Jobber app), plus postcards to dealers listed on brand dealer locators.
**Inputs.** Dealer's co-op statement or brand portal access; program rules PDF per brand; proof of ads (postcard images and print invoices, ad invoices).
**Outputs.** Filed claims with confirmations; a running balance of available, claimed and paid funds per dealer.
**Blocks used.** Document reader (rules and invoices), rules checker (program requirements), portal filer, deadline tracker (program-year expiry), customer layer.
**Running loop.**
Read each brand's program rules into a claim checklist.
Match the dealer's ads against the checklist, including any pre-approval the brand requires.
Assemble proof and file on the brand portal.
Track payout; invoice our share when it posts.
Remind dealers of unspent balances 60 and 30 days before expiry.
**Checks.** Every claim meets every rule on its checklist before submission. Ads that needed pre-approval and didn't get it are never claimed.
**Approval gates.** First claim per brand reviewed by the owner.
**Billing.** 15–25% of recovered funds, charged on payout.
**Edge cases.** Rejected claim: one corrected resubmit, then drop and log the reason in that brand's rules.
Street postcards
**Purpose.** Oversized postcards mailed by USPS Every Door Direct Mail to every home on chosen carrier routes (about 10,000 homes per drop). Two products: a contractor's own "we just installed on your street" card, and a shared card with about 18 local businesses, one per category.
**Customers and channel.** Contractors in the Jobber app; local businesses reached by the shared card itself (each card carries a "your ad here" spot) and by postcards to businesses on the same routes.
**Inputs.** Chosen routes; buyer logos, offers and approvals; for street cards, completed job addresses (street level only, never the homeowner's name).
**Outputs.** Print-ready card files; printer orders with post office drop; proof-approval emails; delivery confirmations.
**Blocks used.** Acquisition engine (mail and design), customer layer, platform connector (Jobber), deadline tracker (fill-by dates).
**Running loop.**
Open a card for a route with a fill-by date.
Offer spots through self-serve checkout at about $550; one business per category.
Design each ad with AI; email the proof; the buyer approves or requests one revision.
When full, or at the fill-by date with enough spots sold, order print with post office drop.
Generate co-op claim proof for any dealer whose brand repays direct mail.
**Checks.** Card meets USPS size and weight specs for EDDM flats; every ad has written approval; no category is sold twice on one card.
**Approval gates.** Owner picks the first towns and approves the first card before print.
**Billing.** Paid at checkout. If a card doesn't fill, buyers are refunded or moved to the next drop.
**Edge cases.** Buyer silent on proof for 5 days: run the proof as designed only if their checkout terms allow it; otherwise refund.
Spec: OSHA filing
**Purpose.** Establishments with 250+ employees, or 20–249 in designated high-hazard industries, must submit their Form 300A injury summary through OSHA's Injury Tracking Application each year, January 2 to March 2, even with zero injuries. We prepare it and submit through the customer's own account.
**Customers and channel.** January postcards to establishments in OSHA's public submission data (385,000+ filed for 2023); offered inside the Jobber app to shops with 20+ staff.
**Inputs.** Establishment name, address, industry code and employee count (from OSHA's public file); the customer's injury log or a zero-injury confirmation; total hours worked and average headcount; executive's name for certification.
**Outputs.** Completed 300A; submission confirmation from OSHA's system; a printable posting copy (required on site February 1 – April 30); next year's reminder.
**Blocks used.** Government data feed (OSHA file), acquisition engine (mail), rules checker (form rules), portal filer, deadline tracker, customer layer.
**Running loop.**
In early December, refresh OSHA's public file and select establishments likely to file again.
Mail postcards the first week of January with a QR link to a pre-filled form.
Customer completes the short form or confirms zero injuries.
Generate the 300A; the executive e-signs certification.
Customer adds us as a delegate on their OSHA account (guided steps); submit and save the confirmation.
Email the posting copy and schedule next year's reminder.
**Checks.** Totals add up; employee and hours figures are plausible for the industry; certification is signed before submission; confirmation saved.
**Approval gates.** First postcard design; first five submissions reviewed by the owner.
**Billing.** $49–199 per establishment per year, paid at checkout.
**Edge cases.** Customer can't add a delegate: deliver the completed file with step-by-step submission instructions and a partial refund. After March 2, stop selling and switch the page to next year's waitlist.
Spec: CPSC data prep
**Purpose.** Since July 8, 2026, imports of products in CPSC's flagged tariff codes (about 600, many of them children's products) need certificate data filed electronically, either in the shipment entry or through CPSC's Product Registry. Foreign-trade-zone entries follow on January 8, 2027. We turn an importer's lab reports and certificates into a valid registry upload file. The importer reviews and certifies; the importer or its customs broker submits.
**Customers and channel.** Customs brokers, who use a white-label portal for all their importers at a flat monthly fee; small importers directly at $19–49 per batch; one public page per flagged tariff code and CPSC rule ("is my product flagged?").
**Inputs.** Lab test reports and existing certificates (PDF); product list; importer details; CPSC's current flagged-code list, rule citation codes and registry template.
**Outputs.** A Product Registry bulk upload file (CSV/Excel) in CPSC's exact template; a gap list of anything missing; for brokers, a per-importer status board.
**Blocks used.** Document reader, rules checker, government data feed (CPSC lists and templates), customer layer, acquisition engine (code pages).
**Running loop.**
Customer uploads documents; the reader extracts the seven required elements: product ID, each applicable CPSC rule, date and place of manufacture, manufacturer, date and place of last test, testing lab, and records contact.
Second engine re-extracts; mismatches become "please check" fields.
Rules checker validates rule codes and lab data against CPSC's lists.
Customer reviews every field beside its highlighted source and certifies.
Generate the upload file and gap list.
Daily: re-download CPSC's lists and template; if anything changed, update the checker, rerun its tests, then release.
**Checks.** Output matches CPSC's template column for column; every rule code is on CPSC's current list; no field is ever invented (a missing value stays blank and appears on the gap list).
**Approval gates.** First broker contract; trade lawyer confirms the flat-fee broker model before any broker launch.
**Billing.** Brokers: flat monthly fee, never per-refund or percentage-based. Direct: per batch at checkout.
**Edge cases.** Unfamiliar lab format: after three failures on the same format, add it to the test set and teach the reader; meanwhile refund that batch.
Spec: Freight claims
**Purpose.** When a trucking carrier loses or damages a pallet shipment, the shipper can claim compensation under federal rules (49 U.S.C. 14706 and 49 CFR Part 370). Carriers must acknowledge a claim within 30 days and resolve it within 120. Many first-time pallet shippers never file. We build and file the claim for shippers who authorize us.
**Customers and channel.** E-commerce brands and small manufacturers using ShipStation, which added pallet (LTL) freight on September 1, 2026, plus a free freight-claim calculator and deadline page.
**Inputs.** ShipStation tracking events and shipment records; delivery receipt with exception notes; photos; commercial invoice; bill of lading.
**Outputs.** A complete claim packet (claimed value, invoice, photos, liability calculation); submission confirmation; a status timeline with the 30- and 120-day deadlines.
**Blocks used.** Platform connector (ShipStation), document reader, deadline tracker, portal filer (carrier claim portals or email), customer layer.
**Running loop.**
Watch tracking for damage, shortage or exception events.
Ask the shipper for photos and the delivery receipt through one link.
Calculate the carrier's liability limit from its published terms.
Build the packet and file it; save confirmation.
Chase acknowledgment at day 30 and resolution at day 120.
Invoice our share when payment arrives.
**Checks.** Claimed value equals the invoice value for the damaged items only; every claim includes required documents; no claim is filed on shipments covered by the shipper's separate insurance unless they ask.
**Approval gates.** First ShipStation app listing; first ten claims reviewed by the owner.
**Billing.** 20–30% of the amount recovered.
**Edge cases.** Carrier offers a settlement with a full release: show the customer the offer and let them accept or decline. Accepting ends the claim.
Spec: Tariff estimator (on hold)
**Purpose.** The Supreme Court struck down IEEPA tariffs on February 20, 2026. CBP refunds through its CAPE process; most of the roughly $166 billion has already been accepted or paid, and the remaining finally-liquidated entries currently require a court case. Only the importer of record or its licensed customs broker may file. We provide a tool that brokers and trade law firms use with their own clients.
**Status.** Build only after a trade lawyer approves the flat-fee model and confirms which deadlines remain. Retire it when the window closes.
**Inputs.** The importer's own customs report (ACE ES-003) uploaded by the broker or law firm.
**Outputs.** A list of possibly refundable entries with amounts and each entry's deadlines (80 days for CAPE after liquidation, 180 days for a protest); pre-filled declaration files for the importer or broker to submit.
**Blocks used.** Document reader, deadline tracker, customer layer.
**Billing.** Flat fee per broker or law firm. Commissions on refunds stay out of every arrangement.
Spec: Recall checker
**Purpose.** Selling a recalled consumer product is illegal under federal law (15 U.S.C. 2068), including secondhand, and CPSC says resellers are required to know recall status. Thrift flippers, consignment shops and online resellers rarely check. We flag recalled items while they browse, scan or upload inventory.
**Customers and channel.** Individual resellers (Chrome Web Store), thrift and consignment stores (batch upload), and scanner or consignment apps (API). One public page per recall number and product name brings search traffic.
**Inputs.** Nightly recall data from CPSC, NHTSA, FDA and FSIS; the listing page the user is viewing (read in their own browser only); scanned barcodes; uploaded inventory CSVs; API queries.
**Outputs.** Per item: "match" with a link to the official recall notice, "no match in CPSC, NHTSA, FDA and FSIS as of [date]", or "uncertain — please check". Flagged CSV for batch uploads. JSON for the API.
**Blocks used.** Government data feed, rules checker (matching thresholds), acquisition engine (recall pages), platform connector (Chrome extension), customer layer.
**Running loop.**
Refresh all recall sources nightly.
Rerun the matching test set (500 known-recalled and 500 known-clean items); block the update if accuracy drops.
Publish new recall pages built from the official records.
Serve matches: exact barcode and model first, then fuzzy brand and model with the local model, then the second engine on borderline cases.
Every "wrong result" report is added to the test set.
**Checks.** At most 1% false "no match" on the test set; borderline cases return uncertain; every recall page shows the recall number, date and official link.
**Approval gates.** First Chrome Web Store submission; first 50 recall pages reviewed by the owner.
**Billing.** $5–9 per month for individuals, $29–79 per month for stores, metered API pricing. A generous free tier for single lookups.
**Edge cases.** The extension reads only the page the user has open and never crawls marketplaces.
Spec: Apify data tools
**Purpose.** Pay-per-use tools on the Apify marketplace that return clean public data, starting with contractor license status in states existing tools don't cover. General contractors and property managers can be liable when a subcontractor's license lapses.
**Customers and channel.** Apify Store search; AI-agent tool directories; our own ventures use the same tools internally.
**Inputs.** License numbers or names; each state board's public lookup site.
**Outputs.** License status, expiry date and source URL, or "unverifiable" when the source can't be read.
**Blocks used.** Government data feed, customer layer (Apify handles billing).
**Running loop (tool factory).**
Pick the next state board, using only boards whose terms allow automated access.
Study the lookup site and record three real license numbers for testing.
Build the tool from the shared template.
A different engine reviews the code and the listing.
Publish; the owner approves the first three publishes, later ones are automatic.
Daily canary run on the three test licenses for every published tool; a broken tool is marked under maintenance and repaired, or retired after two failed repairs.
**Checks.** Test licenses return correct status and expiry; the tool rate-limits itself; sites needing a login or CAPTCHA are skipped.
**Billing.** Per event through Apify (we keep 80% minus platform costs).
Spec: Public-records mail engine
**Purpose.** A shared engine that turns a public list into personalized postcards with a QR code to a pre-filled estimate page. It replaces cold email for OSHA filing, property tax appeals, co-op dealers and importers.
**Inputs.** A public list (OSHA submission file, county assessment roll and notice dates, brand dealer locators, import records); a venture's scoring rule; a card template.
**Outputs.** Address-verified postcards sent through the Lob API; a landing page per recipient with their own numbers; scan and conversion tracking.
**Running loop.**
Pull and refresh the list.
Score each record and keep those above the venture's threshold.
Generate the card and the pre-filled page; verify the address.
Send through Lob; record delivery.
Track QR scans and checkouts; A/B test two card designs per list.
Add any do-not-mail request to the suppression list before the next run.
**Checks.** Every card names the sender clearly and carries no agency-style seals, wording or layout; suppression list applied; per-recipient page shows real figures from the source record.
**Approval gates.** Each new card design and each new list's first send, approved by the owner. Mail spend follows the budget set by the owner.
Spec: Property tax appeals
**Purpose.** Many properties are assessed above market value, and few owners appeal. We build the evidence packet for small landlords in counties the large appeal companies don't serve, and either file it where non-attorney agents are allowed or sell it as a packet the owner files.
**Customers and channel.** Small landlords reached by postcards timed to each county's assessment notice season.
**Inputs.** County assessment roll, notice dates and appeal rules; recent comparable sales; the owner's e-signed authorization.
**Outputs.** An evidence packet with comparables and the requested value; a filed appeal where allowed, or a ready-to-file packet with instructions; decision tracking.
**Blocks used.** Government data feed, mail engine, document reader, portal filer, deadline tracker, customer layer.
**Running loop.**
Per county: load the roll and score parcels for likely over-assessment.
Mail owners of high-scoring rental parcels when notices go out.
Owner checks out (flat packet fee or contingency where allowed) and e-signs.
Build the packet; file or deliver it before the county deadline.
Track the decision; invoice contingency fees after a reduction.
**Checks.** Each county's agent rules confirmed before mailing there; comparables are recent arm's-length sales; filing before the deadline.
**Approval gates.** Each new state before launch (rules differ: Texas requires a registered property tax consultant; Florida limits paid representation to attorneys, CPAs, appraisers and brokers; Cook County needs an attorney).
**Billing.** Flat packet fee, or a share of first-year savings where non-attorney agents may charge one.
**Edge cases.** Counties requiring a live hearing: offer the packet only.
Spec: FDA cosmetics listing tool
**Purpose.** Under the Modernization of Cosmetics Regulation Act (MoCRA), cosmetics makers must register facilities and list products with FDA in a technical XML format (SPL), updating listings yearly and listing new products within 120 days. Small businesses are exempt unless they sell certain products, such as those used near the eyes, products lasting over 24 hours (gel or acrylic nails, permanent hair dye) or injectables. We generate the listing files; the brand submits through FDA's free portal.
**Customers and channel.** Beauty brands just over the small-business line or with many products, found through the Shopify App Store (search ads for the first 90 days) and ingredient and category pages.
**Inputs.** Product list and ingredients from Shopify or upload; facility details; the brand's answers to the exemption checklist.
**Outputs.** A checklist of which products need listing (confirmed by the brand); valid SPL listing files; reminders for the 120-day and annual deadlines.
**Blocks used.** Platform connector (Shopify), document reader, rules checker (FDA's SPL validation rules), deadline tracker, customer layer.
**Running loop.** Read products; brand confirms the checklist; map ingredients with two engines; generate files; validate against FDA's rules; brand submits; parse FDA's response email when forwarded.
**Checks.** Every file passes FDA's validation rules; unsure ingredients go to the brand to confirm.
**Approval gates.** Shopify app submission.
**Billing.** Monthly subscription by product count.
Spec: DIBBS government supply
**Purpose.** The Defense Logistics Agency posts thousands of small parts orders daily on DIBBS. Registered suppliers bid; awards up to $350,000 are often automatic and decided on price.
**Customers and channel.** None needed; the agency posts demand.
**Inputs.** Daily solicitations; quotes from manufacturers and their authorized distributors.
**Outputs.** A ranked bid sheet with margins, and a prepared batch quote file.
**Running loop.** Pull solicitations daily; keep only items open to any supplier and outside electronic parts; request quotes only from the original manufacturer or its authorized distributors; compute margin; prepare the bid exactly as the solicitation asks.
**Approval gates.** The owner signs and submits every bid, because each bid carries legal certifications. Owner approves parts spending.
**Checks.** Part number and supplier match the solicitation exactly; traceability documents on file before shipping.
Spec: Utility audits
**Purpose.** Restaurants often pay sales tax on utilities used in food preparation that a state exempts, and some are on the wrong rate plan. Start with one state with clear exemption rules and a self-serve calculator.
**Inputs.** Utility bills through a data service (UtilityAPI, Arcadia, Green Button) with the customer's permission; the state's exemption rules; the utility's published rates.
**Outputs.** An exemption and rate check; filled state refund forms and utility exemption certificates for the customer to sign.
**Approval gates.** Choice of launch state; any filing needing a power of attorney.
**Billing.** Share of refunds and first-year savings.
Spec: Carpenter's goods
**Purpose.** Sell a local carpenter's handmade furniture online, with the shop in his name and us as manager.
**Running loop.** Clean up his photos, write listings, price from comparable sales, run his Etsy shop and a Shopify site with local pickup, answer routine questions. He handles building, pickup and delivery. Facebook Marketplace posts are made by hand only.
**Billing.** Commission per sale, agreed in writing with him.
Out of scope
These were evaluated and cut. Build nothing for them unless this spec is updated.
| Venture |
Reason
| Motel dynamic pricing |
Target motels have no software to sell through; modern ones already get pricing tools
| Unclaimed property recovery |
State fee caps, licensing rules and free state search tools
| Whop clipping |
About $1 per 1,000 views; account bans forfeit unpaid earnings
| Truck dispatch |
Load board terms ban bots; dispatching for many carriers counts as brokering
| Restaurant delivery refunds |
DoorDash forbids third parties filing disputes; market already full of AI tools
Open questions and caveats
Trade lawyer opinion on the flat-fee broker model (CPSC portal, tariff estimator)
Confirm which tariff refund deadlines remain before building the estimator
Check each brand's warranty portal terms for automated submission before adding that brand
Check Jobber, ShipStation and Shopify marketplaces by hand for competing apps before listing
Pick the launch state for utility audits and the first counties for property tax
Prices, revenue ranges and response rates in this spec are estimates, several from vendor sources. Replace them with measured numbers as soon as each venture has real customers. Regulatory dates change often; the data feed's change alerts are the source of truth, and this spec should be updated whenever they fire.
