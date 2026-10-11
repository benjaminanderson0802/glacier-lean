# Glacier next-work backlog — round 2

**30 scoped launch cards, ranked for first paid pilot, Apify readiness, phase blockers and independent evidence.** Planning snapshot: 2026-10-11, integrated base `22d8d1b` (`origin/glacier-final`). Cards are proposals, not dispatched work or completed checkpoints. No product code, acceptance check or roadmap status was changed by this task.

## T-FIND2 plan and drift check

1. Owner-approved T-FIND2 advances PH12.22 integration planning and identifies remaining phase-exit evidence for PH1–PH10. PH12 is explicitly authorized to proceed while PH5 and PH9 remain `in_progress`; no phase exit is asserted.
2. Dependencies: PH12 depends on PH5/PH9, both still in progress; its work is owner-authorized in parallel. PH3's exit is explicitly owner-approved, but PH3.2 remains in progress and PH3.4's fresh claims metric is invalid. PH1, PH2, PH4, PH5, PH6, PH8 and PH9 remain in progress. Cards only produce scoped evidence/fixes; integrator decides exits.
3. Defining properties: P-VERIFY, P-USABLE, P-CONTROL, P-PORTABLE, P-LOOPS and P-MEMORY. Metrics: M-VERIFIED, M-FALSE-DONE, M-AUDIT, M-PORTABLE, M-LOCAL, M-SURVIVE, M-INTERVENE and M-RECOVER. Each card records its narrow mapping.
4. Existing tools: pytest, current Glacier backend/e2e harness, Apify local SDK, source fixtures, git vault, existing platform adapters and reference room image. No paid service, new framework, or custom workflow system is proposed.
5. Acceptance written first: exactly 30 cards under `.glacier/backlog2/`, each with one exclusive lane, explicit allowed scope, goal, checkpoint/property/metric mapping, existing-tool choice, a falsifiable verification command/result, and exactly one role (`BUILDER` or `TESTER`). Acceptance for the planning task: 30 card files, 30 unique C-prefixed IDs, ranked index, no product/test/checkpoint edits, explicit active-card exclusion map, and `git diff --check` passes. The requested per-folder suites are run and results recorded below.

## Ranking

Value/effort estimates are 1–5 value and 1–3 focused effort units (1 ≈ half a day, 2 ≈ half to one day, 3 ≈ one to two days), excluding owner actions and independent review waits. Higher rank reflects direct pilot readiness, a current blocker, or a missing independent evaluator. Values are planning judgments, not revenue forecasts. Money depends on owner legal/payment readiness, customer response and approval; this backlog performs no outreach, billing, publishing or account work.

| Rank | Card and outcome | Checkpoint | Value | Effort | V/E | Exclusive lane | Role |
| ---: | --- | --- | ---: | ---: | ---: | --- | --- |
| 1 | [C-CLOSEOUT-PILOT-TESTER](C-CLOSEOUT-PILOT-TESTER.md) — independently verify five accurate closeout packets for the $49 offer | PH12.8/22 | 5 | 1 | 5.00 | closeout-pilot-evaluator | TESTER |
| 2 | [C-ALBID-PILOT-TESTER](C-ALBID-PILOT-TESTER.md) — freeze source-linked bid-triage pilot cases | PH12.5/22 | 5 | 1 | 5.00 | al-bid-pilot-evaluator | TESTER |
| 3 | [C-SAM-COLLECTOR-TESTER](C-SAM-COLLECTOR-TESTER.md) — independently verify complete paginated snapshots reach the digest intact | PH12.5 | 5 | 2 | 2.50 | sam-collector-evaluator | TESTER |
| 4 | [C-APIFY-MS-LA-TESTER](C-APIFY-MS-LA-TESTER.md) — independent release and billing-boundary review for existing Actors | PH12.10 | 5 | 2 | 2.50 | apify-existing-actors-evaluator | TESTER |
| 5 | [C-ROOM-VISUAL-TESTER](C-ROOM-VISUAL-TESTER.md) — compare the three frosted-panel room to the exact reference at two sizes | PH5.4/12.1 | 4 | 1 | 4.00 | room-visual-evaluator | TESTER |
| 6 | [C-FLOW-ASSET-STAGING](C-FLOW-ASSET-STAGING.md) — resolve `{repo}` and stage checked-in venture scripts portably | PH12.22 | 5 | 2 | 2.50 | platform-venture-assets | BUILDER |
| 7 | [C-FLOW-ASSET-STAGING-TESTER](C-FLOW-ASSET-STAGING-TESTER.md) — real-backend proof from clean installs | PH12.17/20/22 | 5 | 1 | 5.00 | venture-assets-evaluator | TESTER |
| 8 | [C-FSIS-FEED-REPAIR](C-FSIS-FEED-REPAIR.md) — reproduce and fix the official FSIS API 403 | PH12.5/12 | 4 | 1 | 4.00 | fsis-feed-adapter | BUILDER |
| 9 | [C-PH3-CLAIMS-BENCH-TESTER](C-PH3-CLAIMS-BENCH-TESTER.md) — freeze terminal-proof sampling acceptance | PH3.4 | 5 | 1 | 5.00 | claims-benchmark-evaluator | TESTER |
| 10 | [C-PH3-CLAIMS-BENCH-FIX](C-PH3-CLAIMS-BENCH-FIX.md) — wait for specialist proof before scoring routed cases | PH3.4 | 5 | 2 | 2.50 | claims-benchmark-runner | BUILDER |
| 11 | [C-PH3-PROTECTED-ATTACK-TESTER](C-PH3-PROTECTED-ATTACK-TESTER.md) — independently test symlink, deletion and path attacks | PH3.2 | 5 | 2 | 2.50 | verification-protection-evaluator | TESTER |
| 12 | [C-PH2-LOCAL-WORKER-TESTER](C-PH2-LOCAL-WORKER-TESTER.md) — live offline file-task proof on a free local model | PH2.2 | 5 | 2 | 2.50 | local-worker-evaluator | TESTER |
| 13 | [C-PH2-PORTABILITY-TESTER](C-PH2-PORTABILITY-TESTER.md) — same verified goal through three supported backends | PH2 exit | 5 | 3 | 1.67 | three-backend-evaluator | TESTER |
| 14 | [C-PH1-AUDIT-TESTER](C-PH1-AUDIT-TESTER.md) — test audit events at side-effect and crash boundaries | PH1 exit | 5 | 2 | 2.50 | runtime-audit-evaluator | TESTER |
| 15 | [C-PH5-PLAN-FIDELITY-TESTER](C-PH5-PLAN-FIDELITY-TESTER.md) — check the approved goal/spec reaches the planner unchanged | PH5.2 | 5 | 2 | 2.50 | reviewed-plan-evaluator | TESTER |
| 16 | [C-PH5-SUPERVISOR-TESTER](C-PH5-SUPERVISOR-TESTER.md) — verify the live supervisor honors deterministic evidence | PH5.3 | 5 | 2 | 2.50 | team-supervisor-evaluator | TESTER |
| 17 | [C-PH6-SESSION-PERF-TESTER](C-PH6-SESSION-PERF-TESTER.md) — measure cold/warm metadata listing without dropping sessions | PH6.2 | 4 | 1 | 4.00 | session-discovery-evaluator | TESTER |
| 18 | [C-PH8-CLEAN-STARTUP-TESTER](C-PH8-CLEAN-STARTUP-TESTER.md) — independently test installer without developer Git | PH8.1 | 5 | 2 | 2.50 | desktop-no-git-evaluator | TESTER |
| 19 | [C-PH9-MAINTENANCE-BOARD-TESTER](C-PH9-MAINTENANCE-BOARD-TESTER.md) — verify maintenance in isolated clone/home without legacy destructive scripts | PH9.1 | 4 | 2 | 2.00 | maintenance-board-evaluator | TESTER |
| 20 | [C-TEMPLATE-APPROVAL-TESTER](C-TEMPLATE-APPROVAL-TESTER.md) — freeze reviewed-content approval-swap checks | PH10.4 | 5 | 1 | 5.00 | template-approval-evaluator | TESTER |
| 21 | [C-FEED-IMPORT-TESTER](C-FEED-IMPORT-TESTER.md) — verify exact bytes, vintage and trust boundary on imports | PH12.5 | 4 | 1 | 4.00 | feed-import-evaluator | TESTER |
| 22 | [C-JOBBER-CONNECTOR-TESTER](C-JOBBER-CONNECTOR-TESTER.md) — independently verify read-only completed-job mapping | PH12.8 | 4 | 1 | 4.00 | jobber-connector-evaluator | TESTER |
| 23 | [C-RECALL-BENCHMARK-TESTER](C-RECALL-BENCHMARK-TESTER.md) — source and freeze 1,000 independent recall labels | PH12.12 | 5 | 3 | 1.67 | recall-benchmark-evaluator | TESTER |
| 24 | [C-WARRANTY-RULES-TESTER](C-WARRANTY-RULES-TESTER.md) — verify source-grounded brand rules and uncertainty | PH12.11 | 4 | 2 | 2.00 | warranty-rules-evaluator | TESTER |
| 25 | [C-COOP-FAIL-CLOSED-TESTER](C-COOP-FAIL-CLOSED-TESTER.md) — verify complete draft artifacts never imply filing readiness without evidence | PH12.13 | 4 | 1 | 4.00 | coop-release-evaluator | TESTER |
| 26 | [C-FREIGHT-INTAKE-TESTER](C-FREIGHT-INTAKE-TESTER.md) — check source-to-packet provenance and uncertain cases | PH12.14 | 4 | 1 | 4.00 | freight-intake-evaluator | TESTER |
| 27 | [C-FDA-READER-BOUNDARY-TESTER](C-FDA-READER-BOUNDARY-TESTER.md) — ensure reader disagreement blocks a release-ready FDA packet | PH12.15/4 | 4 | 2 | 2.00 | fda-reader-evaluator | TESTER |
| 28 | [C-OSHA-CSV-TESTER](C-OSHA-CSV-TESTER.md) — independently verify unsigned worksheet field provenance | PH12.16 | 4 | 1 | 4.00 | osha-worksheet-evaluator | TESTER |
| 29 | [C-PROPERTY-TAX-FLOW-TESTER](C-PROPERTY-TAX-FLOW-TESTER.md) — run a safe source case from a fresh real-backend install | PH12.17 | 4 | 1 | 4.00 | property-tax-live-evaluator | TESTER |
| 30 | [C-CARPENTER-COMMISSION-TESTER](C-CARPENTER-COMMISSION-TESTER.md) — independently verify discounts, refunds, fee basis and currency | PH12.20 | 4 | 2 | 2.00 | carpenter-commission-evaluator | TESTER |

## Fresh per-folder test results

Command: `~/w/glacier-lean/.venv/bin/python -m pytest -q <top-level ventures test directory> -ra`, one directory per pytest process; nested `acceptance`/`unit` directories were collected by the parent suite. These are software/fixture checks, not live customer or paid-use evidence. The default run left opt-in public canaries skipped.

| Directory | Result |
| --- | --- |
| `ventures/al-bid-triage/tests` | 25 passed, 1 skipped |
| `ventures/al-license-verify/tests` | 36 passed, 1 skipped |
| `ventures/apify-census-permits/tests` | 9 passed, 1 skipped |
| `ventures/apify-fdic-bankfind/tests` | 10 passed, 1 failed, 1 skipped — test lowercases the message but expects uppercase `FDIC` |
| `ventures/apify-npi-batch/tests` | 11 passed, 1 failed, 1 skipped — same case mismatch for `NPPES` |
| `ventures/apify-portfolio/tests` | 31 passed |
| `ventures/apify-tools-louisiana/tests` | 9 passed, 3 subtests passed |
| `ventures/apify-tools/tests` | 12 passed, 1 skipped, 3 subtests passed |
| `ventures/blocks/connectors/tests` | 18 passed |
| `ventures/blocks/customer/tests` | 22 passed |
| `ventures/blocks/deadlines/tests` | 6 passed |
| `ventures/blocks/feeds/tests` | 26 passed |
| `ventures/blocks/filer/tests` | 3 failed — Node cannot resolve Playwright in this worktree |
| `ventures/blocks/mail/tests` | 13 passed |
| `ventures/blocks/reader/tests` | 3 passed |
| `ventures/blocks/rules/tests` | 3 passed |
| `ventures/carpenter-goods/tests` | 20 passed |
| `ventures/coop-postcards/tests` | 16 passed |
| `ventures/cpsc-prep/tests` | 26 passed, 1 skipped (rerun after B-CPSC-RELEASE integration) |
| `ventures/dibbs-supply/tests` | 29 passed (rerun after M-DIBBS integration) |
| `ventures/fba-fee-check/tests` | 26 passed, 1 skipped |
| `ventures/fda-cosmetics/tests` | 17 passed |
| `ventures/freight-claims/tests` | 35 passed |
| `ventures/job-closeout/tests` | 21 passed, 1 skipped |
| `ventures/osha-filing/tests` | 22 passed |
| `ventures/property-tax/tests` | 47 passed, 1 failed — legacy unit assertion hard-codes prior-day date `2026-10-10` |
| `ventures/recall-actor/tests` | 13 passed, 2 skipped, 3 subtests passed |
| `ventures/recall-checker/tests` | 20 passed |
| `ventures/sam-amendment-alerts/tests` | 34 passed, 1 skipped (rerun after F-SAM2 integration; prior fixture failure is fixed) |
| `ventures/utility-audits/tests` | 15 passed (rerun after B-UTILITY-FORM integration) |
| `ventures/warranty/tests` | 23 passed |
| `ventures/tests` | 22 passed |

The currently failing targeted checks are left unchanged. The two Apify case-only assertion failures are recorded in their `DISPUTE.md`; the property-tax date assertion is stale against the current date. F-SAM2 and the earlier SAM acceptance fixes are integrated and the full SAM suite now passes. The filer failure is environmental and matches the existing Playwright claims. After the concurrent integrations, DIBBS, CPSC, utility and `ventures/tests` were rerun. No `RUN_LIVE=1`, publication, payment, or owner-account action was performed.

## Launch contract

- Dispatch each card on `card/<ID>` from the current integrated base only after confirming the listed paths are not actively edited. One writer per exclusive lane. Cards with `after` dependencies can prepare their independent inputs now, but implementation/evaluation runs in the order stated on the card.
- Role is exclusive. A **BUILDER** owns only the listed implementation lane, adds ordinary unit coverage where authorized, and never edits the independent acceptance/evaluator check. A **TESTER** owns only its listed new check/data/evidence, does not change product behavior, and never edits the check that evaluates its own test tooling. Never combine roles on one card.
- Reproduce before editing. Preserve existing test IDs and behavior. Keep failing/skipped results visible; no xfail, loosened assertion, skipped check or fabricated live proof.
- Use the project interpreter `~/w/glacier-lean/.venv/bin/python`. Behavior changes need focused tests and real-backend proof as specified in `docs/TESTING.md`; use a disposable home and unique port. Never stop another worker's process.
- Screen work must match `glacier/web/src/theme/limbo/room.webp`: painted room, exactly three frosted panels, Nunito, lowercase chrome and token-only colors. Keep the mock in step and preserve every `data-testid` and existing behavior.
- At a checkpoint, the integrator—not these cards—runs `setup/run_core_tests.sh` and `setup/live_codex_check.sh` when appropriate, commits evidence and updates only checkpoint `status`/`evidence`. Do not edit NORTHSTAR exit criteria or open decisions.
- Owner/customer actions remain owner-only: operating/legal/payment readiness, prospect contact, price choice, payout/identity verification, publication, signatures, filings, mail and customer data permission. This backlog does none of them. No card guarantees revenue.

## Active-card exclusion map

The following running cards are explicitly excluded from this backlog's product paths. Recheck their actual launch prompt and worktree status at dispatch.

| Running card | Reserved work not assigned here |
| --- | --- |
| M-FIX1 | screen merge, lowercase cleanup and home/automation/venture screenshots; C-ROOM-VISUAL-TESTER uses a separate new e2e file after integration |
| M-DIBBS | DIBBS intake, bid-sheet traceability and daily feed alerts; merged during this planning pass |
| F-SAM2 | SAM builder-owned no-match fixture in `tests/test_digest.py`; merged during this planning pass. C-SAM-COLLECTOR-TESTER uses a separate new acceptance file and never edits the fixture |
| T-WINPORT2 | Windows portability changes across venture acceptance checks; still active at final review |
| B-MAIL-SUPPRESSION | mail address normalization and suppression |
| B-CPSC-RELEASE | CPSC source/template release protection; merged during this planning pass |
| B-SUPPORT-REPLAY | customer reply idempotency |
| B-UTILITY-FORM | utility application rendering and proof; merged during this planning pass |
| T-APIFY3B | new Census, FDIC and NPI Actor work; C-APIFY-MS-LA-TESTER covers only the pre-existing Mississippi/Louisiana Actors |

No card enters these reserved paths. The broader first-round cards that landed are treated as integrated context, not reissued work. The current DIBBS, mail, customer and utility lanes are left out of this round where the explicit running cards own the area.

## Phase and venture disposition

- PH1 runtime exit needs independent audit coverage; PH2 needs actual local execution and three-backend swap proof; PH3 needs protected-file attacks and a valid claim benchmark remeasurement.
- PH4 checkpoints are recorded built; the memory reinstall card is independent reconfirmation. PH5 remains in progress with reviewed-plan fidelity and live supervisor findings. PH6 remains dependent on two weeks of owner use; the session timing card is only bounded technical evaluation. PH8.1 still lacks auto-update and clean startup without developer Git. PH9's self-build history needs a safe maintenance-board reconfirmation.
- PH12 technical cards prioritize the closeout and Alabama bid pilot evidence, existing Apify Actor verification, SAM digest correctness, portable venture assets and high-value independent checks. DIBBS has a consent/policy gate; mail/customer/CPSC/utility reserved work is excluded; tariff remains blocked by owner counsel. Do not infer commercial permission from public access or account connectivity.

## Findings and anti-pattern review

- Round 1's check results changed on the integrated base: Alabama bid, Alabama roster, FBA, job-closeout, carpenter, freight, OSHA and other venture tests now pass. SAM's six earlier acceptance issues were fixed in `0c305fe`, and F-SAM2 fixed the stale unit fixture; do not repeat their previous builder fixes without a fresh failing reproduction.
- Current unaddressed software/environment failures are recorded in the result table; current Filer dependency errors are not application evidence. Existing Apify case-sensitivity disputes and the SAM fixture dispute remain visible. The stale property-tax date assertion should be handed to its independent check owner, not edited by a product builder.
- Anti-patterns: this is a requested planning deliverable, but 30 cards risk task fragmentation. The ranking therefore places pilot readiness and phase blockers first, uses unique lanes, and routes evaluation separately from implementation. No checkpoint status, customer-success claim, paid tool or new governance system is introduced.
