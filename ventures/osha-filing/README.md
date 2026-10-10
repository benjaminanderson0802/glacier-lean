# OSHA filing preparation

This workflow prepares a customer-reviewed OSHA 300A annual summary worksheet from the establishment's own injury log and hours data. The OSHA ITA feed is a prospecting/reference list only; it does not prove that a business is covered or determine whether it must file. The customer confirms coverage, all values, and the executive certifier. Glacier does not certify, submit, or claim to have received an OSHA confirmation.

The generated JSON review worksheet is not an official OSHA form or submission confirmation. The executive uses the official OSHA ITA account to complete, certify, and submit the annual summary, then saves the confirmation and posts the signed copy from February 1 through April 30. If OSHA coverage or values are uncertain, preparation stops for customer review. After March 2, new sales must wait for the next cycle.

## Your steps

1. Confirm coverage and establishment details using the [OSHA recordkeeping overview](https://www.osha.gov/recordkeeping).
2. Review, certify, and submit the annual summary in [OSHA's Injury Tracking Application](https://www.osha.gov/injuryreporting/ita) between January 2 and March 2.
3. Post the signed summary from February 1 through April 30 and save the customer-provided ITA confirmation in the local job folder.

## Run locally

```sh
~/w/glacier-lean/.venv/bin/python -m ventures.blocks.feeds.cli sync osha_ita
~/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/filing.py prepare --intake "$GLACIER_HOME/ventures/osha-filing/incoming/intake.json" --output "$GLACIER_HOME/ventures/osha-filing/out"
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/osha-filing/tests
```

The intake JSON includes `establishment` (`name`, `address`, `industry_code`, `employees`), `year`, `injury_log`, `hours_worked`, `average_employees`, `executive_name`, `executive_title`, `coverage_confirmed`, and `customer_confirmed`. The injury log includes deaths, days-away cases, job-transfer/restriction cases, other recordable cases, and their days counts. The workflow checks nonnegative totals and broad plausibility; the employer remains responsible for accurate OSHA recordkeeping and coverage decisions.

No live postcard, checkout, account signup, delegated filing, or external mail action is enabled. OSHA ITA data is public and can be refreshed from the official source via the shared feed. The feed reader has transfer and row limits to stop unexpectedly large downloads.
