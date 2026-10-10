# Warranty registration

This venture prepares warranty intake records for HVAC contractors. It reads jobs through the shared read-only Jobber connector, checks the model and serial against independent readings and configured brand rules, calculates a registration deadline, and flags items due within ten days. The output is a review queue; a `match` is not a legal conclusion or proof of warranty coverage.

The local rules use 60 days for Trane, Goodman, Daikin, and Lennox and 90 days for Carrier, based on the Venture Build Spec. California and Quebec are skipped; Lennox units in Florida or Georgia installed on or after January 1, 2026 are also skipped. These are intake rules only. Product eligibility and warranty coverage remain the contractor/homeowner's call.

## Portal automation status

Terms were checked on 2026-10-10. No brand is enabled for automated portal access or submission. Daikin's published terms prohibit automated systems to monitor or copy its sites. Trane's official site terms require express prior written permission for automated page monitoring or copying; the warranty portal's applicability needs an owner check. The public material reviewed for Goodman, Lennox, and Carrier did not clearly authorize automated portal submission, so each also needs an owner check before it is added. No credentials are requested or used by this venture yet. The shared filer is imported behind a warranty helper that only accepts localhost, for its test mock. Customer authorization and a saved approval are still required for any future filing.

- [Daikin Terms of Use](https://daikincomfort.com/terms-of-use)
- [Trane website terms](https://www.trane.com/content/dam/Trane/Commercial/global/terms-and-conditions-of-use.pdf)
- [Trane registration](https://www.trane.com/residential/en/resources/warranty-and-registration/register/)
- [Goodman registration](https://warranty.goodmanmfg.com/newregistration/)
- [Lennox registration](https://www.lennox.com/residential/owners/register-and-review/product-registration/index)
- [Carrier registration](https://productregistration.carrier.com/Public/RegistrationForm_Carrier?brand=carrier)

The terms check is not legal advice. The owner should confirm current terms directly with each brand before enabling any portal workflow.

## Run a local intake check

Create a JSON file containing normalized records with `job_id`, `completed`, `brand`, `model_reading`, `model_confirmation`, `serial_reading`, `serial_confirmation`, `installed_on`, `region`, `homeowner_name`, and `homeowner_email`. Do not put portal passwords in this file. To evaluate it:

```sh
~/w/glacier-lean/.venv/bin/python -m ventures.warranty.scripts.warranty evaluate --input ./install-records.json --as-of 2026-10-10
```

The default configuration has no verified brand serial formats, so real records stay `uncertain — please check` until an owner provides source-backed format rules. The opt-in missing-photo output is only a draft; this venture does not send texts or emails.

## Serial-format availability and human fallback

No brand has a configured serial pattern. This is deliberate: a brand stays unavailable to automatic serial validation until its official format is documented from a source the owner has reviewed. Records for all five listed brands currently remain `uncertain — please check`; do not infer a pattern from sample numbers. For a real unit, use the brand's official warranty page linked in `venture.json` or contact the brand/dealer, verify the serial manually, and keep registration under owner review. Portal automation remains disabled.

## Jobber launch prerequisites

Create an app in the [Jobber Developer Center](https://developer.getjobber.com/) and use its [API documentation](https://developer.getjobber.com/docs/). Save `jobber_client_id`, `jobber_client_secret`, `jobber_access_token`, and `jobber_refresh_token` in Glacier under **Settings → Secrets**, then run the read-only connector check. Launch intake is still blocked until the shared connector returns completed status, install date, homeowner name and email, brand, model, serial, region, and job ID; five eligible test accounts pass; and the shared reader and deadline blocks are integrated. Use local sample JSON until then.

The first Jobber listing and first 20 generated homeowner email drafts are owner-review gates. Drafts are not currently generated because the shared mail block is not integrated; this venture does not send email.

## Your steps

1. Create the Jobber developer app/test account and save its values in Glacier Secrets. Run the shared connector check.
2. Confirm portal terms and official serial formats brand by brand. Daikin automation is disabled by its published terms.
3. Review the first marketplace listing and first 20 homeowner email drafts before launch. Neither is published or sent by this build.

Paid billing is not enabled. Stripe or Jobber billing needs a separate owner-approved configuration.
