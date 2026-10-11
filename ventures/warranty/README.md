# Warranty registration

This venture prepares warranty intake records for HVAC contractors. It reads Jobber GraphQL jobs through the shared read-only connector, maps account-labeled text fields for brand/model/serial/install date, calculates registration deadlines, and builds a local review queue plus homeowner email drafts. Drafts are never sent. A `match` is not a legal conclusion or proof of warranty coverage.

The local rules use 60 days for Trane, Goodman, Daikin, and Lennox and 90 days for Carrier, based on the Venture Build Spec. California and Quebec are skipped; Lennox units in Florida or Georgia installed on or after January 1, 2026 are also skipped. These are intake rules only. Product eligibility and warranty coverage remain the contractor/homeowner's call.

## Portal automation status

Terms were checked on 2026-10-10. No brand is enabled for automated portal access or submission. Daikin's published terms prohibit automated systems to monitor or copy its sites. Trane's official site terms require express prior written permission for automated page monitoring or copying; the warranty portal's applicability needs an owner check. The public material reviewed for Goodman, Lennox, and Carrier did not clearly authorize automated portal submission, so each also needs an owner check before it is added. No brand portal credentials are requested or used. The shared filer is imported behind a warranty helper that only accepts localhost, for its test mock. Customer authorization and a saved approval are still required for any future filing.

- [Daikin Terms of Use](https://daikincomfort.com/terms-of-use)
- [Trane website terms](https://www.trane.com/content/dam/Trane/Commercial/global/terms-and-conditions-of-use.pdf)
- [Trane registration](https://www.trane.com/residential/en/resources/warranty-and-registration/register/)
- [Goodman registration](https://warranty.goodmanmfg.com/newregistration/)
- [Lennox registration](https://www.lennox.com/residential/owners/register-and-review/product-registration/index)
- [Carrier registration](https://productregistration.carrier.com/Public/RegistrationForm_Carrier?brand=carrier)

The terms check is not legal advice. The owner should confirm current terms directly with each brand before enabling any portal workflow.

## Run the owner Jobber check

After the owner has saved the four Jobber values in Glacier **Settings → Secrets**, run this one command from the repository root:

```sh
~/w/glacier-lean/.venv/bin/python ventures/warranty/scripts/owner_check.py
```

At run time, the connector reads OAuth values from Glacier's OS keychain. It makes read-only GraphQL requests using API version `2026-04-16`, writes the local pending deadline input to `GLACIER_HOME/ventures/warranty/pending-units.json` (or `~/.glacier/...`), and prints the registration queue with unsent homeowner drafts. Credentials are not printed. The local queue contains Jobber customer data and stays on this machine. The Jobber test account must have text custom fields labeled Brand, Model, Serial, and Install Date (the Equipment-prefixed labels are also recognized).

Real serial formats remain unverified for every brand, so records return `uncertain — please check` and stay on owner review even when a deadline can be calculated. A draft is not a registration confirmation; no email or portal submission occurs.

## Run a local intake check

Create a JSON file containing normalized records with `job_id`, `completed`, `brand`, `model_reading`, `model_confirmation`, `serial_reading`, `serial_confirmation`, `installed_on`, `region`, `homeowner_name`, and `homeowner_email`. Do not put portal passwords in this file. To evaluate it:

```sh
~/w/glacier-lean/.venv/bin/python -m ventures.warranty.scripts.warranty evaluate --input ./install-records.json --as-of 2026-10-10
```

The default configuration has no verified brand serial formats, so real records stay `uncertain — please check` until an owner provides source-backed format rules. The opt-in missing-photo output is only a draft; this venture does not send texts or emails.

## Serial-format availability and human fallback

No brand has a configured serial pattern. This is deliberate: a brand stays unavailable to automatic serial validation until its official format is documented from a source the owner has reviewed. Records for all five listed brands currently remain `uncertain — please check`; do not infer a pattern from sample numbers. For a real unit, use the brand's official warranty page linked in `venture.json` or contact the brand/dealer, verify the serial manually, and keep registration under owner review. Portal automation remains disabled.

## Jobber launch prerequisites

Create an app in the [Jobber Developer Center](https://developer.getjobber.com/) and use its [API documentation](https://developer.getjobber.com/docs/). Save `jobber_client_id`, `jobber_client_secret`, `jobber_access_token`, and `jobber_refresh_token` in Glacier under **Settings → Secrets**, then run the read-only owner check. The fixture-tested connector now requests completed status/date, install fields, homeowner name/email, and property region, and the local loop prepares a deadline queue and unsent drafts. Live-account behavior is not yet verified; use local sample JSON until the owner configures the test account and verifies five eligible records. The shared reader and deadline blocks remain separate PH12 work, but the warranty loop currently calculates its own deadline.

The first Jobber listing and first 20 generated homeowner email drafts are owner-review gates. The warranty check prepares the drafts locally; the shared mail block is not integrated and this venture does not send email.

## Your steps

1. Create the Jobber developer app/test account and save its values in Glacier Secrets. Run the shared connector check.
2. Confirm portal terms and official serial formats brand by brand. Daikin automation is disabled by its published terms.
3. Review the first marketplace listing and first 20 homeowner email drafts before launch. Neither is published or sent by this build.

Paid billing is not enabled. Stripe or Jobber billing needs a separate owner-approved configuration.
