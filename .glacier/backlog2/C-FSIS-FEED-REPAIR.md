# C-FSIS-FEED-REPAIR — Restore the official FSIS recall API canary

Owner: Benjamin. Role: **BUILDER only**.

## Scope

Exclusive lane: `fsis-feed-adapter`. Allowed product edit: `ventures/blocks/feeds/core.py`; ordinary unit tests may be added under `ventures/blocks/feeds/tests/unit/` with this card ID. Do not edit the recall checker, source registry, acceptance checks, or network policy. Begin from a fresh context and reproduce the exact 403 before changing code.

## Goal

Investigate the documented request-header difference in `CLM-2026-10-10-B2-FSIS-API-403`. Make the smallest compliant request change so the official read-only FSIS endpoint yields validated records, while outages remain source errors rather than confident empty results.

Read first: claim `2026-10-10-b2-fsis-api-403.md`, `ventures/blocks/feeds/CHECK.md`, `ventures/blocks/feeds/README.md`, `ventures/recall-checker/PROOF.md`.

## Drift check

- Checkpoint: PH12.5, unblocking PH12.12. PH5/PH9 remain in progress; PH12 is owner-authorized parallel work.
- Properties/metrics: P-VERIFY, P-LOOPS; M-VERIFIED, M-SURVIVE.
- Existing tools: current stdlib HTTP client and feed registry; no new service or dependency.
- Acceptance first: captured official response parses into expected dated fields; malformed/403/timeout cases remain uncertain/error and never become no-match.

## Verification

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/feeds/tests`. One polite read-only official GET is allowed if the fixture suite passes. Follow the NORTHSTAR two-attempt cap and stop on a repeated/stuck signal; no change to access terms or authentication.
