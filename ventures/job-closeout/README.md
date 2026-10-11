# Job Closeout Packet Builder

## What it does

The prototype reads completed jobs through Glacier's existing read-only `JobberClient` and writes a customer handoff packet as Markdown and PDF on the selected local folder. It uses the job title/date, customer name and service location, configured Jobber text fields, equipment details, and invoice reference. It adds two photo placeholders for the shop to replace with customer-approved photos.

The packet is a record of supplied job details. It does not certify workmanship, code compliance, safety, warranty coverage, registration eligibility, or a warranty deadline. Missing source fields are shown as **uncertain — please check**. The warranty section is a reminder to check the manufacturer's current terms; no OEM portal is visited and no registration is submitted.

The current read-only connector does not fetch invoice objects or photo attachments. To include an invoice reference, create a Jobber text custom field named `Invoice Reference`. Configure `Work Summary`, `Equipment Brand`, `Equipment Model`, and `Equipment Serial` as text fields when those are useful to the shop.

## Who pays

The hypothesis is owner-operated HVAC or plumbing shops that already use Jobber and want a consistent customer-ready closeout record. The prospect list identifies public business-directory entries; it does not establish that a business uses Jobber or has this pain.

## Price hypothesis

Offer a **$49 paid pilot for up to 10 packets** after a shop confirms the sample reflects its workflow. Compare each packet with the source job and have the shop correct any errors. Only propose an ongoing price after learning whether the pilot saved time. This is an unvalidated price hypothesis, not a signed offer.

## Owner steps

1. Send the pitch in [PILOT.md](PILOT.md) to one business from [prospects.csv](prospects.csv). The owner edits and sends it manually; the prototype has no email or outreach capability.

If a buyer wants a pilot, get their authorization and agree the pilot scope and terms before touching customer records or charging. The subsequent optional Jobber mode requires the account owner's Jobber authorization and secrets saved in Glacier's keychain. Never paste secrets into files, email, or the vault. Fixture mode needs no secrets and makes no network requests.

## Run locally

```bash
~/w/glacier-lean/.venv/bin/python ventures/job-closeout/scripts/generate_packet.py \
  --fixture ventures/job-closeout/tests/fixtures/jobber_completed_job.json \
  --output-dir /path/to/packets
```

For a shop-authorized account already connected through Glacier, use `--jobber` instead of `--fixture`. The script reads at most five pages, filters to completed jobs, writes only local Markdown/PDF files, and never sends or files anything. Review every output before sharing it. Delete customer uploads within 30 days after a pilot job closes unless the customer asks to keep them.

## Acceptance check first

The fixture-based acceptance checks require a completed Jobber-shaped job to produce a readable Markdown packet and valid PDF, reject an upcoming job, mark missing details uncertain, and call the existing Jobber client only through its read-only methods. Fixture processing is also checked to make no network connection. Run:

```bash
~/w/glacier-lean/.venv/bin/python -m pytest ventures/job-closeout -q
```

This advances PH12 as an in-scope venture artifact. PH12 depends on PH5 and PH9, which are owner-approved for start in this wave; `NORTHSTAR.yaml` records the phase as in progress. It serves P-GOALS and P-LOOPS through a repeatable owner-run packet workflow and M-INTERVENE by reducing manual packet assembly; M-TTFA remains a portfolio metric, not measured here. The existing Jobber connector covers the API access need, so this prototype adds only packet-generation glue and local PDF output. No additional external tool is introduced.
