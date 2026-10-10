---
id: CLM-PH12-22-CPSC-INTEGRATION-GAP
filed_by: I2
run_id: null
node_id: null
checkpoint: PH12.22
kind: capability_gap
summary: CPSC batch integration has no configured feed IDs and its flat fields do not satisfy the merged CPSC ruleset
evidence: "Inspected `ventures/blocks/feeds/sources.json`: it has no `cpsc_flagged_tariff_codes`, `cpsc_rule_codes`, or `cpsc_registry_template` IDs required by `cpsc_prep.py`. Reproduced `ventures.blocks.rules.check(fields, 'cpsc_efiling.json')` with the venture's flat field shape: verdict `fail`; product_id passed, citation_codes was uncertain, manufacture_date/manufacture_place failed, product_test_date/testing_laboratory/point_of_contact were uncertain."
attempts_made: 1
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

## Impact

The CPSC batch cannot pass its merged rules check or obtain current flagged-code, rule-code, and exact-template data from the installed feed registry. The flow fails closed and does not release a CSV, but the venture cannot meet its release check.

## Required resolution

Coordinate the CPSC venture with the feed owner and rules owner: provide current official CPSC list/template feeds and a field mapping that preserves the SPEC's source pages, required elements, structured locations, and date precision. Add independent tests for that mapping, then rerun the public-data batch and real Glacier flow. Do not bypass the rules result or mark the venture released while this claim is open.
