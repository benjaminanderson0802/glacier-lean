# Warranty registration

This venture prepares warranty intake records for HVAC contractors. It reads Jobber GraphQL jobs through the shared read-only connector, maps account-labeled text fields for brand/model/serial/install date, calculates registration deadlines, and builds a local review queue plus homeowner email drafts. Drafts are never sent. A `match` is not a legal conclusion or proof of warranty coverage.

The local rules use the cited eligible-product windows for Trane, Goodman, Daikin, Lennox, and Carrier. California and Quebec are skipped; Lennox units in Florida or Georgia installed on or after January 1, 2026 are also skipped. These are intake rules only. Product eligibility and warranty coverage remain the contractor/homeowner's call.

## Portal automation status

Official-source registration and serial guidance is stored as data in [`brands/`](brands/). It covers Carrier/Bryant, Trane/American Standard, Lennox, Rheem/Ruud, Goodman/Amana, and Daikin. The queue carries the matching family's source links, deadline guidance, registrant options, terms status, and date-code note. Where a product/jurisdiction rule or permission is not stated clearly, the data says `uncertain - please check`.

No brand is enabled for automated portal access or submission. Some official portals explicitly support a homeowner or installing-dealer/representative role; that does not establish permission for an outside service to prepare data or for automation. Daikin's terms prohibit automated systems from monitoring or copying its sites. Trane's site terms require prior written permission for automated monitoring/copying, and applicability to the registration flow still needs owner review. No portal credentials are requested or used. The shared filer remains behind a localhost-only mock helper. Customer authorization and a saved approval would still be required for any future filing.

- [Daikin Terms of Use](https://daikincomfort.com/terms-of-use)
- [Trane website terms](https://www.trane.com/content/dam/Trane/Commercial/global/terms-and-conditions-of-use.pdf)
- [Brand-by-brand registration and date-code records](brands/)

The terms check is not legal advice. The owner should confirm current terms directly with each brand before enabling any portal workflow.

## Run the owner Jobber check

After the owner has saved the four Jobber values in Glacier **Settings → Secrets**, run this one command from the repository root:

```sh
~/w/glacier-lean/.venv/bin/python ventures/warranty/scripts/owner_check.py
```

At run time, the connector reads OAuth values from Glacier's OS keychain. It makes read-only GraphQL requests using API version `2026-04-16`, writes the local pending deadline input to `GLACIER_HOME/ventures/warranty/pending-units.json` (or `~/.glacier/...`), and prints the registration queue with unsent homeowner drafts. Credentials are not printed. The local queue contains Jobber customer data and stays on this machine. Create the four Job Text fields using the exact names in [`JOBBER-SETUP.md`](JOBBER-SETUP.md).

Serial validation remains disabled for every brand, so records return `uncertain — please check` and stay on owner review even when a deadline can be calculated. The `brands/` records include official date-code descriptions where available, scoped to the cited product families. A draft is not a registration confirmation; no email or portal submission occurs.

## Run a local intake check

Create a JSON file containing normalized records with `job_id`, `completed`, `brand`, `model_reading`, `model_confirmation`, `serial_reading`, `serial_confirmation`, `installed_on`, `region`, `homeowner_name`, and `homeowner_email`. Do not put portal passwords in this file. To evaluate it:

```sh
~/w/glacier-lean/.venv/bin/python -m ventures.warranty.scripts.warranty evaluate --input ./install-records.json --as-of 2026-10-10
```

The records document official date-code descriptions where published, but the queue does not parse serial codes: it has no enabled brand serial patterns, and intake records stay `uncertain — please check` until independently checked. The opt-in missing-photo output is only a draft; this venture does not send texts or emails.

## Serial-format availability and human fallback

No brand has an enabled serial pattern. Published date-code descriptions for Lennox, Rheem, Goodman, Amana, and a specific Daikin product family are recorded in the brand data, with their model-specific limits. Carrier/Bryant and Trane/American Standard remain `uncertain - please check` for a general residential HVAC date code. Do not infer a pattern from sample numbers. For any real unit, use the brand's official warranty page or contact the brand/dealer, verify the serial manually, and keep registration under owner review. Portal automation remains disabled.

## Jobber launch prerequisites

Create an app in the [Jobber Developer Center](https://developer.getjobber.com/) and use its [API documentation](https://developer.getjobber.com/docs/). Save `jobber_client_id`, `jobber_client_secret`, `jobber_access_token`, and `jobber_refresh_token` in Glacier under **Settings → Secrets**, then run the read-only owner check. Follow the exact two-minute field setup in [`JOBBER-SETUP.md`](JOBBER-SETUP.md). A five-job local GraphQL-shaped fixture was run through the real Glacier engine; this verifies the local workflow only. Live-account behavior still requires the owner to configure the test account and verify five eligible records. The shared reader and deadline blocks remain separate PH12 work, and this warranty loop calculates its own reminders.

The first Jobber listing and first 20 generated homeowner email drafts are owner-review gates. The warranty check prepares the drafts locally; the shared mail block is not integrated and this venture does not send email.

## Your steps

1. Create the Jobber developer app/test account and save its values in Glacier Secrets. Run the shared connector check.
2. Confirm portal terms and official serial formats brand by brand. Daikin automation is disabled by its published terms.
3. Review the first marketplace listing and first 20 homeowner email drafts before launch. Neither is published or sent by this build.

Paid billing is not enabled. Stripe or Jobber billing needs a separate owner-approved configuration.
