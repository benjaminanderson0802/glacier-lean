---
id: claim-ph12-16-osha-shared-blocks
filed_by: Codex
run_id: card/gf-V-OSHA
node_id: ventures.blocks.rules, ventures.blocks.feeds, ventures.blocks.deadlines
checkpoint: PH12.16
kind: capability_gap
summary: OSHA filing cannot be integrated against its required shared rules, government-data-feed, and deadline-tracker blocks because those packages are absent from this checkout.
evidence: "`/home/glacier/w/glacier-lean/.venv/bin/python` import probe: ventures.blocks.customer/filer/mail available; ventures.blocks.rules, ventures.blocks.feeds, and ventures.blocks.deadlines each raise ModuleNotFoundError. `ventures/README.md` also marks those three blocks not integrated."
attempts_made: 0; stopped immediately because the required shared-block outputs are missing from another lane; no substitutes or edits to shared blocks attempted.
status: closed
assigned_to: integrator
resolution: "The shared rules, feeds, and deadlines packages were merged into the base before this resumed card. The OSHA venture now imports and uses their public interfaces; no shared block implementation was added here."
resolution_evidence: "ventures/osha-filing/tests/test_osha_filing.py — 6 passed (includes shared rules/deadlines imports and deadline behavior); ventures/install_all.py --only osha-filing --dry-run validates all four flows; OSHA live feed sync returned rows=400288, changed=false, alerts=[]."
---

## Resolution

The shared `rules`, `feeds`, and `deadlines` blocks are now present on this card's base branch. The OSHA venture imports them, passes its focused tests, validates its four flows, and the live OSHA feed reports 400,288 rows with no alerts. The old missing-block condition is resolved. No shared block files were changed by this card. No customer accounts, credentials, real outreach, signatures, or portal submissions were used.
