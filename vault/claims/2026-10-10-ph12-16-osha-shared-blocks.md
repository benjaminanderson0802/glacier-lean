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
status: filed
assigned_to: integrator
resolution: ""
resolution_evidence: ""
---

## Blocker

PH12.16's spec requires the government data feed (OSHA public ITA data), rules checker (Form 300A validation), and deadline tracker (Jan 2–Mar 2 filing window). Their packages and release checks are not present under `ventures/blocks/`, so the venture cannot import the fixed interfaces or satisfy its acceptance checks on this base branch.

The mail, filer, and customer packages are present. The official OSHA ITA public-data page is reachable at https://www.osha.gov/itadata. No OSHA venture files were added because writing local replacements would duplicate shared-block responsibilities and violate the one-owner rule.

## Next step

Merge the shared rules, feeds, and deadlines blocks (including their `README.md`, `CHECK.md`, and tests), then resume this card and wire the OSHA-specific flow to those interfaces. No accounts, credentials, outreach, signatures, or portal submissions were attempted.
