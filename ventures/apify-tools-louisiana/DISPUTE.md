# Dataset schema test update for builder — 2026-10-11

Update `tests/test_independent_actor_billing.py::test_dataset_output_schema_declares_every_emitted_column` to read declared column names from `schema["fields"]["properties"]`. Keep both assertions intact so every emitted column and every displayed field must still be declared.

Apify documents `fields` as a JSON Schema object, with column definitions under `fields.properties`: [Dataset schema specification](https://docs.apify.com/platform/actors/development/actor-definition/dataset-schema). The current page redirects to Apify's Storage dataset schema documentation, which shows `fields: {"type": "object", "properties": {...}}`.
