---
id: CLM-2026-10-10-PH12-13-COOP-POSTCARDS-CAPABILITY-GAPS
filed_by: V-COOP
run_id: null
node_id: null
checkpoint: PH12.13
kind: capability_gap
summary: Co-op claim and EDDM postcard launch depends on missing shared blocks and connector capabilities
evidence: "ventures/blocks contains only customer, connectors, filer and mail; reader, rules, and deadlines contracts are not implemented. JobberClient only exposes read-only jobs and no in-app dealer surface. MailBlock postcard hardcodes 6x4 while the spec requires EDDM flats. Filer.prepare stores portal session state only in process memory, so a draft cannot survive a separate approval pause. install_all registers flows but does not stage venture scripts into the flow workspace; the disposable live run needed a temporary workspace symlink."
attempts_made: 1
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

## Impact

PH12.13 cannot pass its release checks from this base. Without the document reader and shared rules checker, program rules and evidence cannot be checked with the required independent mechanism. Without the deadline tracker, due reminders cannot be scheduled through the shared contract. The Jobber connector has no app UI for dealer intake. The current postcard renderer creates a 6x4 card, which does not prove the spec's oversized EDDM flat check. The filer holds prepared browser state in a process-global cache, so prepare and submit cannot safely be separated across Glacier's approval wait.

The venture-local claim guard deliberately returns `uncertain` and prevents filing when the shared rules checker is missing. The card does not add replacements for the block contracts.

The live smoke check also showed that `install_all.py` registers the flow definitions but does not make the venture's command scripts available under Glacier's per-flow workspace. The successful runtime smoke check used a temporary symlink in the disposable test home; a normal fresh install has no such symlink. Staging venture scripts is an installer/integrator change outside this card's file lane.

## Alternatives checked

1. Imported the existing `ventures.blocks` interfaces and inspected each available block's `README.md` and `CHECK.md`; the `reader`, `rules`, and `deadlines` packages are absent. Filer and mail have a `CHECK.md` but no README.
2. Considered implementing the missing shared decision logic inside the venture. Rejected because the spec requires shared blocks and a second-engine/script check, and NORTHSTAR I-01 says not to duplicate a tool that covers the need.

## Required resolution

Merge the assigned reader, rules, and deadline blocks; update the installer to stage each venture's scripts into its flow workspace; add an approved Jobber app intake surface; provide a mail-block format/release check that supports USPS EDDM flats in Lob test mode or a compatible print workflow; and make portal filer drafts resumable across Glacier approval waits. Then update this venture to call those contracts and re-run its acceptance checks.
