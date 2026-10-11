# OSHA filing preparation — owner steps

## Current status: blocked

The live OSHA ITA Summary Data page and its exact page-linked CSV URL returned HTTP 403 from this script client on 2026-10-11. The DOL Open Data API catalog has no ITA Summary Data dataset. Glacier's automated canary recorded the failure and correctly prepared zero worksheets. No owner download or browser workaround is counted as a completed source check.

**There is no owner action to take while this source block remains.** Once script access to an official source is restored, Glacier will refresh it, validate the unique establishment-ID canary, and create up to five drafts automatically.

## First review when the source is available

1. Open `$GLACIER_HOME/ventures/osha-filing/worksheets/first-five-status.json`, then open each of the up to five HTML files named there. Confirm the source link and compare every value with the establishment's own records before using a draft. The output folder is local; no file is uploaded. About 4 minutes per worksheet. Do not sign or file from these public historical values.

Run the preparation command only if you need to repeat the automatic refresh:

```sh
~/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py prepare-first-five --as-of YYYY-MM-DD
```

No live outreach is enabled. This venture relies on written postcard or marketplace outreach, so outreach stays optional and minimal.

## Customer's legal filing action

For any actual customer filing, that establishment's executive must personally compare the current records, complete any missing information, certify and sign, post the signed summary February 1–April 30, and submit required data through the customer's own [OSHA ITA account](https://www.osha.gov/injuryreporting/) by March 2. See OSHA's [official Form 300A and instructions](https://www.osha.gov/recordkeeping/forms). Glacier never certifies, signs, posts, or submits.
