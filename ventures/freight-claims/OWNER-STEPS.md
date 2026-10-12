# Owner steps — freight claims

Status: **ready for owner action**. The ShipStation partner route is not a confirmed app-store listing. Its official public page offers an integration-partner inquiry, but does not publish acceptance criteria, listing placement, or commercial terms. This package does not agree to spend or bind the owner.

## One launch setup sitting (about 35–65 minutes)

Open [ShipStation's API and custom-store partner page](https://info.shipstation.com/become-a-partner-api-and-custom-store-integrations), then use its partner inquiry form. The page can also be reached from [ShipStation's partnership options](https://www.shipstation.com/partnership-options/) → **Integration or Technology Partner** → **Apply Now**.

The form is rendered dynamically, so its current field labels should be checked on the page. Use the account holder's real contact and business details. Do not invent or infer the legal business name, website, address, EIN, or phone number; these are not stored in this repository.

For a free-text “tell us about your integration” field, paste:

> Glacier Freight Claims prepares source-linked claim-packet drafts and deadline reminders for merchants who identify a possible lost, damaged, or short shipment. With the merchant's authorization, Glacier reads shipment records through a read-only ShipStation connection; merchants can instead provide their own Shipments or Orders CSV export. The shipper confirms the exception, damaged-item value, documents, insurance status, and carrier terms. Glacier prepares a review packet and reminder timeline. The shipper signs and submits the claim directly to the carrier and records the carrier receipt. Glacier does not create or change shipments, buy labels, send carrier messages, sign, file claims, or accept settlements. We are seeking written guidance on eligibility, any app-directory/listing review, required technical or security checks, and all fees or revenue-share terms before deciding whether to proceed. No paid service or commercial terms have been accepted.

Before submitting, confirm that the form is an inquiry only and that submitting it does not accept terms, authorize charges, or enroll the business in a paid service. ShipStation describes partner applications and separate agreements; commercial terms are not published on the public partner page. If the form requires acceptance of unpublished paid terms, stop and ask for written terms first. Do not use a phone call; request a written reply.

## Listing copy prepared for a later approved listing

**Working title:** Freight Claim Packet Preparation for ShipStation Merchants

**Short description:** Prepare a source-linked draft packet and follow-up dates for a shipment exception the shipper confirms.

**Description:** Glacier reads shipment records through an authorized read-only ShipStation connection or a merchant-provided Shipments/Orders CSV export. A possible exception is only a prompt for the shipper to review. Glacier joins it to customer-confirmed claim details and local supporting documents, prepares an evidence checklist and draft packet, and tracks dates after the shipper records the carrier's receipt. The shipper reviews all details, signs and submits directly to the carrier, and decides any settlement. Glacier does not file claims, contact carriers, buy labels, or guarantee recovery. API use is subject to ShipStation account eligibility and limits; current live account use is not verified.

**Price:** Not set. Owner approval and any applicable partner terms are required before pricing or publication.

**Support, privacy, and company URLs:** Not supplied in the repo. Fill only with owner-verified published details if ShipStation requests them. Do not publish this draft as a listing until ShipStation confirms the route and the owner approves the final listing.

In the same sitting, choose one intake path and review the first ten packets:

- **API:** confirm the ShipStation account meets its current API-plan requirement and that the documented daily request cap fits the account quota; save the read-only API key in Glacier Settings → Secrets; enable polling explicitly and check its first read.
- **CSV:** export **Shipments** or **Orders** from ShipStation and place the file at `$GLACIER_HOME/ventures/freight-claims/incoming/`.

Review the first ten distinct packets against each source document, the shipper's confirmations, the exact carrier service terms, and insurance status. Keep uncertain or missing facts unresolved. If the account would need a paid plan change or quota purchase, use CSV instead; no spending is authorized. The current proof is synthetic; it does not establish live account access.

## Per-claim actions belong to the shipper/customer

For each claim, the shipper confirms the details and evidence, provides or signs any owner-approved authorization, files directly with the carrier, records the receipt/reference and responses, and accepts or declines any full-release settlement. The owner reviews an invoice draft before sending or charging. These actions cannot be done by Glacier.

## Prepared references

- [ShipStation partner route](https://info.shipstation.com/become-a-partner-api-and-custom-store-integrations)
- [ShipStation API authentication](https://docs.shipstation.com/authentication)
- [ShipStation API rate limits](https://docs.shipstation.com/rate-limits)
- [ShipStation partner account approval note](https://www.shipstation.com/docs/api/accounts/create/)
- [Local incoming-file instructions](incoming/README.md)
- [Customer intake checklist](incoming/CUSTOMER-INTAKE.md)
