# Jobber setup (about five minutes)

The flow reads completed **Jobs**. It does not create or edit Jobber data. Create the four account-level Job fields below once, then enter the matching values on each completed installation job.

## Create the four Job fields

In Jobber, click **Gear → Settings → Custom Fields → Jobs → Add Field**. For each row, set **Applies to: Jobs**, paste the exact **Name**, choose **Text**, leave the default value blank, and leave **Transferable Field** unchecked (non-transferable). In short: leave the default blank. Keep the fields internal to the Jobber account. Save each field.

| Name to paste | Type | Default | Example job value |
| --- | --- | --- | --- |
| `Equipment Brand` | Text | blank | `Carrier` |
| `Equipment Model` | Text | blank | `Infinity 24 25VNA4` |
| `Equipment Serial` | Text | blank | `2126E12345` |
| `Install Date` | Text | blank | `2026-05-11` |

Use the install date format `YYYY-MM-DD`. Do not use the Job's completed date as a substitute. Enter real equipment values on the actual job; the examples above are format examples only. If Jobber already has one of these fields, reuse it only if its name and type match exactly.

The Jobber Help Center documents the Gear → Settings → Custom Fields path, the Jobs level, Text type, default value, and transferable setting. The Jobber API documentation confirms Jobs expose custom fields and support Text values. The feature is available only on select Jobber plans; do not upgrade a plan just for this step without the owner's separate approval. See [Jobber custom fields](https://help.getjobber.com/en/articles/custom-fields/) and [Jobber API custom fields](https://developer.getjobber.com/docs/using_jobbers_api/custom_fields/).

## Fields Glacier reads

The Jobber GraphQL reader selects `CustomFieldText { id label valueText }` and maps the exact labels above. It also reads job completion status, client name/email, and the property's region. It sends GraphQL queries only and does not request the Custom Field Configurations write scope. See [Jobber's GraphQL API overview](https://developer.getjobber.com/docs/).

The field definitions are not enough to prove a live account connection. The owner setup checklist is in [`OWNER-STEPS.md`](OWNER-STEPS.md). Jobber's GraphiQL-issued access token is testing-only and expires after 60 minutes; it is not a recurring production connection. A production OAuth callback and marketplace release remain outside this venture-preparation card. No owner should publish an app or give Glacier a paying contractor's data as part of this step.
