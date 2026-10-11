# Jobber setup (about two minutes)

This is a **Job** custom-field setup step. The warranty flow reads completed jobs and does not create or edit Jobber data. Jobber custom fields are account-level definitions with per-object values; the connector reads only Job `CustomFieldText` values by label.

## Create four fields

In Jobber, open **Settings → Custom fields → Jobs** and create these fields. Choose the **Text** value type for every field. Put the value on each completed installation job:

| Exact field name | Jobber type | Example value |
| --- | --- | --- |
| Equipment Brand | Text | Carrier |
| Equipment Model | Text | Infinity 24 25VNA4 |
| Equipment Serial | Text | 2126E12345 |
| Install Date | Text | 2026-05-11 (ISO `YYYY-MM-DD`) |

The connector also recognizes `Brand`/`Manufacturer`, `Model`, `Serial`/`Serial Number`, and `Installation Date`/`Installed On`, but use the exact names above to keep the mapping predictable. Do not use a Jobber date field for Install Date: it is a custom **Text** field and the value should be ISO formatted. The job's completed timestamp is read separately and is not treated as the installation date.

## Why these fields match the API

Jobber's official GraphQL docs say custom fields are available on Jobs, configured at the account level, and support a Text value type. The query's `Job.customFields` selection is `__typename` plus `... on CustomFieldText { id label valueText }`; only Text custom fields are mapped. The query selects `Job { id jobNumber title jobStatus completedAt jobberWebUri }`, `Client { id name email }`, and `Property { id address { city province postalCode country } }`. The connector maps the text labels to brand/model/serial/install date, uses `completedAt` or `jobStatus` only to establish completion, gets homeowner name/email from the client, and derives the region from the property's `province` (or `state`) unless a Region/State/Province Job field is present. It sends `X-JOBBER-GRAPHQL-VERSION: 2026-04-16`. It uses GraphQL **queries only**; it has no Jobber mutation path.

Jobber docs:

- [Custom fields](https://developer.getjobber.com/docs/using_jobbers_api/custom_fields/) — Jobs support custom fields; Text is a supported type; fields are configured at account level.
- [GraphQL API overview](https://developer.getjobber.com/docs/) — endpoint, version header, IDs and schema overview.
- [API version changelog](https://developer.getjobber.com/docs/changelog/) — active version changes; no breaking change affecting this read query is listed for `2026-04-16`.

The docs say custom fields are available on Jobber's Connect plan or higher. An account admin creates these four fields manually. Glacier does not create them through the API or ask for the Custom Field Configurations write scope.
