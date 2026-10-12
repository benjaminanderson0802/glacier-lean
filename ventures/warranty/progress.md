# Warranty registration progress

## PH12.11 release-gate acceptance criteria (written before this card's edits)

1. Six reviewed brand-family records cover Carrier/Bryant, Trane/American Standard, Lennox, Rheem/Ruud, Goodman/Amana, and Daikin; each has an official brand portal URL, source-backed deadline/registrant detail where stated, conservative portal-terms status, and an official source for any date-code format. Unclear facts say `uncertain - please check`.
2. A five-job fixture passes through the queue builder and queue entries include the matching brand-family registration guidance; no serial pattern is inferred, records remain held when validation is unverified, and all generated drafts remain unsent.
3. `JOBBER-SETUP.md` confirms the read-only GraphQL query against Jobber's official docs/version and names the four exact Job custom fields and Text types for the owner setup step.
4. The real Glacier engine runs the warranty intake flow on those five local fixture jobs and commits run/API/output evidence in `PROOF.md`; no brand portal or Jobber write, registration submission, or email occurs.
5. `ventures/warranty`, `ventures/coop-postcards`, and `ventures/blocks` test suites remain green. `ACCEPTANCE.md` and `tests/acceptance/` are read-only for this card.

## Drift check

1. Checkpoint: PH12.11, Warranty registration.
2. Dependencies: PH5 and PH9 have not reached their exits. PH12 is owner-approved and this card explicitly authorizes work in wave 6, so the card may start; this card cannot mark PH12 or its exits complete.
3. Defining properties and metrics: P-GOALS (completed-install intake becomes a runnable recurring flow), P-CONTROL / M-AUDIT (Jobber reads stay read-only and drafts remain unsent), P-VERIFY / M-VERIFIED (deterministic deadline calculation and explicit uncertainty), and P-USABLE / M-TTFA (one-command check after initial secret setup).
4. Existing tools: extended the shared read-only Jobber connector and reused the existing warranty deadline rules. A small mapping and draft builder are venture glue; no new dependency was added. The shared reader and deadline blocks remain separate PH12 work, and the live Jobber account cannot be verified until the owner configures its OAuth values in Glacier's keychain.
5. Acceptance tests written before implementation: the connector must request and parse Jobber GraphQL job status/completion, custom text fields, client, and property fields using API version 2026-04-16; the response fixture must flow to a calculated warranty queue and an unsent email draft; unknown serial patterns must remain `uncertain — please check`. Commands and results are in `PROOF.md`.

## PH12.11 release-gate drift check

1. **Checkpoint:** PH12.11, Warranty registration.
2. **Dependencies:** PH5 and PH9 exits are incomplete. PH12 wave 6 and V-WARRANTY are explicitly owner-approved, so work may start; this card cannot mark the checkpoint complete.
3. **Property and metric:** P-CONTROL / M-AUDIT (read-only Jobber and no external actions), P-VERIFY / M-VERIFIED (source-backed rules and explicit uncertainty), P-GOALS / M-TTFA (usable Jobber-to-queue flow).
4. **Existing tools:** the shared read-only Jobber GraphQL connector and Glacier engine/approval nodes already cover transport and orchestration. Venture-specific mapping and brand evidence are missing; use the existing connector/engine and local JSON only, with no dependency or portal automation.
5. **Acceptance test, written first:** the five criteria above; particularly fixture queue inspection and a real Glacier engine run of the committed warranty intake flow using a disposable local-fixture override, plus the three requested existing test boards. No edits to acceptance checks.

Engine-run reproduction note: the real engine completed the five-fixture flow, but its 20,000-character stdout limit retained only the tail because every queue item embedded the entire brand record (including repeated source lists). The fix is limited to emitting the queue fields needed for review plus a local brand-record reference; full official citations stay in `brands/*.json`. The flow will be rerun after this compacting change.

Implemented the Jobber job query, a synthetic API-shaped fixture with realistic encoded IDs/custom fields/client/property/completion data, mapping from Jobber field labels to the warranty intake shape, queue/draft generation, local queue persistence for the daily deadline flow, and `scripts/owner_check.py`. The one-command check resolves secrets from Glacier's keychain at runtime; it never includes token values in output. Drafts are output for owner review and never sent. No brand serial pattern is enabled and no portal is automated.

The warranty suite passes (20 passed); the connector plus warranty suites pass (38 passed). These are fixture-backed results, not live account evidence. The live owner-check attempt stopped before network access because `jobber_access_token` is absent from this worktree's Glacier secret store. Existing synthetic Glacier dry-run evidence is documented in `PROOF.md`, but it does not verify the new live connector path. Other venture suites and the unrelated Recall Checker/portal-filer test failures are listed in `PROOF.md`. Five-account verification, marketplace publication, and email review/send remain owner steps. No checkpoint status was changed.
