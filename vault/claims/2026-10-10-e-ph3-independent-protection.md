---
id: CLM-2026-10-10-E-PH3-INDEPENDENT-PROTECTION
filed_by: worker:E-PH3
run_id: ''
node_id: ''
checkpoint: PH3.2
kind: capability_gap
summary: Independent coverage and pre-work provenance are still needed for protected acceptance files
evidence: evidence/E-PH3/before-symlink.json; evidence/E-PH3/after-protected-files.json; glacier/backend/verify.py
attempts_made: 1
status: filed
assigned_to: verifier
resolution: ''
resolution_evidence: ''
---

## Problem

The existing verification tests cover content edits, but do not independently cover symlink redirection, deleted protected files, or changes outside a declared `files` map. The builder must not write the acceptance/security checks judging its own verifier changes (I-04).

## Evidence

`before-symlink.json` records the original verifier overwriting an outside file while rejecting the worker's modified check. The implementation now inspects the private copy with lstat, rejects links/reparse points and non-regular protected paths, compares all protected files, then restores them. `after-protected-files.json` is a builder-run diagnostic, not independent acceptance: file/parent/dangling links are rejected without outside writes; unchanged and absent protected files pass.

Absence is still ambiguous: a verifier-owned file supplied only in the saved flow is intentionally allowed to be absent from the worker workspace. The current verifier has no pre-work snapshot to distinguish that from a worker deleting an existing protected file. A complete I-04 claim needs independent adversarial coverage and, for deletion detection, a runtime snapshot or equivalent provenance before work starts. Do not mark this claim resolved just because existing content-edit tests pass.

## Research

Use the existing pytest and verification benchmark infrastructure, stdlib path inspection, and existing run graph/workspace snapshot facilities. No external tool or paid service is required. The independent tester should add cases from the invariant, including file and parent links, broken links, wrong file types, portable path traversal, deleted checks, and verifier-only absent checks. A runtime/integrator lane must coordinate any pre-work snapshot changes in runner/store; this card's production fix touches only verify.py.

## Resolution

Pending independent verifier coverage and coordinated runtime provenance work. No owner-only decision is made here.

The existing `setup/selfbuild/protected_guard.py` already compares baseline file hashes and rejects deletion in the self-build lane (`test_protected_guard_rejects_deleted_check`). Reuse that baseline principle for generic flows rather than inventing another governance mechanism; no self-build guard or test was changed by this card.
