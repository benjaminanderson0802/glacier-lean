# Glacier remaining-work backlog

**30 scoped launch cards, ranked by estimated value/effort.** Planning snapshot: 2026-10-10, base commit `c17f52c0fbb4c9cc3bb49baaf7acec116d83c3e4`. These are proposals ready for assignment, not running jobs or claims of completed checkpoints. No product code, acceptance check, roadmap state or owner decision was changed by T-FIND.

## T-FIND plan and drift check

1. Benjamin’s 2026-10-10 “maximize progress” instruction explicitly authorizes this planning-only card. It advances PH12.22 integration planning and identifies work for PH7, PH10 and PH11 alongside PH12; it does not assert a phase exit.
2. PH12 depends on PH5 and PH9, both recorded in progress. The card authorizes planning now; exit claims must wait for dependency evidence. PH3 and PH7 have explicit owner exit decisions. Full dependency ledger follows below.
3. Primary properties: P-VERIFY, P-USABLE, P-LOOPS and P-CONTROL; primary metrics: M-VERIFIED, M-INTERVENE, M-SURVIVE and M-AUDIT. Each card supplies its narrower mapping.
4. Existing tools: use git, rg, existing tests, existing framework adapters and the existing health runner. No new tool, paid service or governance system is proposed merely to manage this backlog.
5. Acceptance specified before writing: exactly 30 individually scoped cards plus a ranked index; each names its goal, source evidence, checkpoint, properties/metrics, dependency/lane constraints and verification; no edits to running-card files, product code or acceptance checks. Review with file count, scope diff and `git diff --check`; independent review remains the integrator’s job. No executable test was written to judge this planning work.

## Ranking

Value is an estimate from 1–5: 5 protects important approvals/data or removes a multi-venture release blocker; 4 improves reliability or delivers a usable artifact; 3 closes a narrower correctness/usability gap. Effort units estimate focused worker time: 1 ≈ up to half a day, 2 ≈ half to one day, 3 ≈ one to two days. They exclude human approvals, unavailable environments and independent evaluation waits. Rank sorts value/effort, then value, then ID; it is not a revenue forecast. Security and scope gates override numerical rank.

| Rank | Card and outcome | Checkpoint | Value | Effort | V/E | Exclusive lane |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 1 | [B-CLOSEOUT-PATH](B-CLOSEOUT-PATH.md) — Keep closeout packets inside their output directory | PH12.8 | 5 | 1 | 5.00 | closeout |
| 2 | [B-FILER-SETUP](B-FILER-SETUP.md) — Make the portal filer runnable from a clean worktree | PH12.7 | 5 | 1 | 5.00 | filer |
| 3 | [B-PROPERTY-NUMBERS](B-PROPERTY-NUMBERS.md) — Reject non-finite property values before preparing packets | PH12.17 | 3 | 1 | 3.00 | property |
| 4 | [B-TEMPLATE-PREVIEWS](B-TEMPLATE-PREVIEWS.md) — Generate missing template previews from their real graphs | PH10.2 | 3 | 1 | 3.00 | template-artifacts |
| 5 | [B-FEED-QUARANTINE](B-FEED-QUARANTINE.md) — Keep suspect source updates out of trusted feed snapshots | PH12.5 | 5 | 2 | 2.50 | feeds |
| 6 | [B-MAIL-SECRETS](B-MAIL-SECRETS.md) — Keep mail credentials in the keychain and on the approved host | PH7.3, PH12.7 | 5 | 2 | 2.50 | mail |
| 7 | [B-READER-LABELS](B-READER-LABELS.md) — Independently complete the reader release benchmark | PH12.4 | 5 | 2 | 2.50 | reader-evaluator |
| 8 | [B-SIGNATURE-AUTH](B-SIGNATURE-AUTH.md) — Protect the local signature server from unsolicited requests | PH7.2, PH12.6 | 5 | 2 | 2.50 | customer |
| 9 | [B-BID-REVISIONS](B-BID-REVISIONS.md) — Keep later supplied bid notices from being silently discarded | PH12.5 | 4 | 2 | 2.00 | al-bid |
| 10 | [B-CLOSEOUT-PDF](B-CLOSEOUT-PDF.md) — Preserve customer names and equipment text in closeout PDFs | PH12.8 | 4 | 2 | 2.00 | closeout |
| 11 | [B-HEALTH-VENTURES](B-HEALTH-VENTURES.md) — Include isolated venture suites in integration health reporting | PH11.1 | 4 | 2 | 2.00 | health |
| 12 | [B-MAIL-PROOF](B-MAIL-PROOF.md) — Make local postcard proofs show all of the reviewed content | PH12.7 | 4 | 2 | 2.00 | mail |
| 13 | [B-MAIL-SUPPRESSION](B-MAIL-SUPPRESSION.md) — Honor do-not-mail requests across equivalent address spellings | PH12.7 | 4 | 2 | 2.00 | mail |
| 14 | [B-PAYMENT-STATUS](B-PAYMENT-STATUS.md) — Stop treating a checkout return URL as payment evidence | PH12.6 | 4 | 2 | 2.00 | customer |
| 15 | [B-READER-OCR](B-READER-OCR.md) — Provide a reproducible local photo-reading prerequisite | PH12.4 | 4 | 2 | 2.00 | reader-runtime |
| 16 | [B-ROSTER-HEADERS](B-ROSTER-HEADERS.md) — Make roster field mapping deterministic when columns conflict | PH12.10 | 4 | 2 | 2.00 | al-roster |
| 17 | [B-SAM-INTEGRITY](B-SAM-INTEGRITY.md) — Reject misleading comparisons of incomplete SAM snapshots | PH12.5 | 4 | 2 | 2.00 | sam-digest |
| 18 | [B-DEADLINE-DELIVERY](B-DEADLINE-DELIVERY.md) — Prevent a crash from silently consuming a reminder | PH12.5 | 5 | 3 | 1.67 | deadlines |
| 19 | [B-FILER-BINDING](B-FILER-BINDING.md) — Bind portal submission to the prepared destination and fields | PH7.1, PH12.7 | 5 | 3 | 1.67 | filer |
| 20 | [B-FILER-RECOVERY](B-FILER-RECOVERY.md) — Avoid re-filing when a portal succeeds before the local receipt is saved | PH12.7 | 5 | 3 | 1.67 | filer |
| 21 | [B-SAM-COLLECT](B-SAM-COLLECT.md) — Collect bounded SAM snapshots for the existing pilot | PH12.5 | 5 | 3 | 1.67 | sam-collector |
| 22 | [B-DIBBS-INTAKE](B-DIBBS-INTAKE.md) — Trace bid-sheet inputs back to owner-verified solicitation records | PH12.19 | 3 | 2 | 1.50 | dibbs |
| 23 | [B-PIN-INVENTORY](B-PIN-INVENTORY.md) — Make the existing health report account for venture dependency pins | PH11.1 | 3 | 2 | 1.50 | health |
| 24 | [B-CPSC-RELEASE](B-CPSC-RELEASE.md) — Prevent a changed CPSC template from silently changing batch output | PH12.9 | 4 | 3 | 1.33 | cpsc |
| 25 | [B-CUSTOMER-RESTORE](B-CUSTOMER-RESTORE.md) — Make customer records recoverable without the original SQLite database | PH12.6 | 4 | 3 | 1.33 | customer |
| 26 | [B-FEED-IMPORT](B-FEED-IMPORT.md) — Import owner-downloaded official data with provenance | PH12.5 | 4 | 3 | 1.33 | feeds |
| 27 | [B-OFFLINE-PROOF](B-OFFLINE-PROOF.md) — Prove the offline pack works without network access | PH10.3 | 4 | 3 | 1.33 | offline-evaluator |
| 28 | [B-SUPPORT-REPLAY](B-SUPPORT-REPLAY.md) — Prevent duplicate support replies during retries and concurrent sends | PH12.6 | 4 | 3 | 1.33 | customer |
| 29 | [B-TEMPLATE-BOUNDARY](B-TEMPLATE-BOUNDARY.md) — Independently verify imported template provenance and approval boundaries | PH10.4 | 4 | 3 | 1.33 | template-evaluator |
| 30 | [B-UTILITY-FORM](B-UTILITY-FORM.md) — Produce a reviewable unsigned utility application artifact | PH12.18 | 3 | 3 | 1.00 | utility |

## Launch contract

- Dispatch a card on `card/<ID>` from the integrated base only after checking that its allowed paths still have no active writer. Commit small changes; never push. Read AGENTS.md, NORTHSTAR.yaml in full, ORCHESTRATION.yaml, the card and its evidence links. The original orchestration PR/merge instructions do not authorize these workers to push or merge.
- Ready means its first scoped reproduction or implementation/evaluation step can start without an owner purchase, publication, new account or legal ruling. It does **not** mean all 30 can edit simultaneously, that a live external check is available, or that an unverified defect is already proven. Code observations explicitly require reproduction before a fix. Retire a stale card with evidence rather than inventing new scope.
- One writer per exclusive lane. Cards touching the same file are serialized. Suggested lane orders: filer SETUP → BINDING → RECOVERY; feeds QUARANTINE → IMPORT; customer SIGNATURE-AUTH → PAYMENT-STATUS → SUPPORT-REPLAY → CUSTOMER-RESTORE; mail SECRETS → SUPPRESSION → PROOF; closeout PATH → PDF; health HEALTH-VENTURES → PIN-INVENTORY. Reader evaluator owns labels independently of the reader runtime builder; neither edits the other’s files. SAM collector and digest use separate files but agree additive metadata before integration.
- Card goals specify acceptance before code. Builders may add ordinary unit tests, but an independent evaluator must own/freeze any missing check that will judge completion. Existing `tests/acceptance/`, `ACCEPTANCE.md`, `CHECK.md`, benchmark runners and other judging checks are read-only. Tester-only cards are assigned to someone who did not build the implementation and cannot change product code. Request no agent delegation implicitly from this backlog.
- Reuse existing free/OSI-licensed tools when they meet the need. Any additional dependency needs pinning, maintenance/license evidence and ordinary project review. $0 paid cap remains; an existing platform adapter is not authorization to adopt a new paid/closed service. Official CLI/API routes and already configured owner keys only.
- Reproduce within the lane before editing. Maximum two self-fix attempts, second from fresh context; stop at a NORTHSTAR stuck signal. For an out-of-lane error, new capability, unclear contract or policy issue, file a card-specific claim and hand it to its owner. Do not modify another worker’s files or judging test. No claim is closed on self-report.
- Behavior changes require the relevant existing suite plus a real backend run in a disposable GLACIER_HOME using `~/w/glacier-lean/.venv/bin/python` and docs/TESTING.md. Use unique ports and only stop processes the worker started. A real engine with synthetic inputs is **fixture-through-engine proof**, not customer or production proof. Browser/local mock, public-source, account-sandbox, owner-hardware and customer evidence must be labeled separately.
- Preserve every existing behavior/test ID and existing API contract unless the integrator explicitly assigns a contract change. These cards authorize no Glacier screen, mock-server, active flow, main installer or shared-contract edits. If UI work is later separately assigned, use theme tokens, Nunito and lowercase room chrome, maintain the mock, and run TypeScript, theme, i18n, build and related e2e checks.
- At an actual checkpoint, the integrator runs `setup/run_core_tests.sh` and `setup/live_codex_check.sh` when workers are involved, commits evidence and updates only checkpoint status/evidence. None of these cards independently edits NORTHSTAR or its exit criteria.
- All spending, sending, publication, signatures, filings, account/identity/payout setup, destructive owner-data changes, legal decisions and price choices remain owner/customer actions. Synthetic local files and mock effects are the default. No tariff-estimator build; no new venture is authorized by research rankings.

## Active-card exclusion map

Read the actual launch prompts in `/home/glacier/tools/cards/gf-<ID>.md`, not just IDs. Those files are outside this checkout; this is the portable scope summary at planning time. Recheck at dispatch because worktrees are moving.

| Running cards | Reserved work omitted from these 30 cards |
| --- | --- |
| U-ROOM | Room scene, shell/panels, navigation, right-panel live engine data |
| U-SCREENS | Center screens, canvas/graph, controls and their real endpoint wiring |
| U-VENTURES | Nested venture view, owner steps, installed run/canary data and run-now UI |
| E-PH1 | Core backend runtime, scheduling, approvals and recovery |
| E-PH2 | Worker routes, local/subscription models and portability proofs |
| E-PH3 | Core independent-check enforcement, false-done detection and claims |
| E-PH4 | Memory engine/API, graph/search and reinstall evidence |
| E-PH5 | Assistant/planner/backend and unverified PH5 work |
| E-PH6 | Daily AI hub, imports/session mirror and document/web backend |
| E-PH8 | Tauri/sidecar, packaging, desktop installation and auto-update |
| E-PH9 | Self-build, verified merges and maintenance workflows |
| V-AUTOMATE | `ventures/install_all.py` and venture flows, schedules/canaries/alerts; includes the property-tax approval-edge failure |
| A-CASH | FASTEST-MONEY/OWNER-TODAY, Actor listing READMEs, PRICING, pilot offers and prospects |
| RG-FDA | FDA release gates, reader-consumer contract, benchmark/runtime fixes within that venture |
| RG-RECALL | Recall release gates, labeled 500/500 matching benchmark and matcher fixes |
| RG-WARRANTY | Brand/serial rules, Jobber mapping and five-job engine proof; shared consumers are read-only here |
| G-CARPENTER3 | Commission-basis/refund/currency fixes and the protected commission checks |

No card edits `glacier/backend`, `glacier/web`, `ventures/*/flows`, install_all.py, active sales materials or the FDA/recall/warranty/carpenter implementations. Shared-block cards preserve consumer APIs and rerun affected consumers after integration; fixes needing active backend or flow changes are explicit handoffs.

## All-phase review and dependencies

Checkpoint status is not equivalent to proof of every phase exit. This ledger records the source file, not a new status decision.

| Phase | Recorded prerequisites/status and disposition |
| --- | --- |
| PH0 | Done, no dependencies. Toolset/legacy foundation has linked evidence; no new foundation rewrite card. |
| PH1 | Depends PH0 (done); in progress despite built checkpoints. Runtime/audit follow-up reserved for E-PH1. |
| PH2 | Depends PH1 (in progress); in progress. Real local/laptop/swap evidence reserved for E-PH2 and owner hardware. |
| PH3 | Depends PH2 (in progress); phase field in progress, explicit owner exit approval 2026-10-07. E-PH3 owns core follow-up. |
| PH4 | Depends PH1 (in progress); in progress. Reinstall/shared memory reserved for E-PH4. |
| PH5 | Depends PH3/PH4 (phase fields in progress, PH3 exit approved); in progress. Assistant work reserved for E-PH5 and U-SCREENS. |
| PH6 | Depends PH2/PH5 (in progress); in progress. E-PH6 owns implementation; two-week owner-use exit cannot be manufactured by a worker. |
| PH7 | Depends PH3 (owner exit approved); done with explicit owner exit decision. Additive shared-block security cards apply its protections to venture surfaces; do not reopen or rewrite the phase. |
| PH8 | Depends PH1 (in progress), PH7 (done); in progress. Desktop/update and real-PC proofs reserved for E-PH8/owner. |
| PH9 | Depends PH3/PH5/PH7; explicit PH3/PH7 exits, PH5 in progress. In progress; E-PH9 owns self-build evidence. |
| PH10 | Depends PH8/PH9 (in progress); in progress with built checkpoints. Offline proof, template preview artifacts and independent import-boundary evaluation are unclaimed, scoped follow-ups. |
| PH11 | Depends PH10 (in progress); in progress. Existing health runner misses venture coverage/dependency inventory. PH11.3/11.4 referenced by old orchestration are absent from current NORTHSTAR: do not revive them. |
| PH12 | Depends PH5/PH9 (in progress); explicitly owner-authorized parallel work. Build/reliability follow-ups can start, but external live-use, payment and dependency exits remain separate gates. PH12.21 stays blocked. |

## Venture/research review

Read [OWNER-START-HERE](../../ventures/OWNER-START-HERE.md), [SPEC](../../ventures/SPEC.md), [ORCHESTRATION](../../ORCHESTRATION.yaml), per-block CHECKs, relevant PROOF/ACCEPTANCE files and all five research reports: [R-APIFYGAPS](../../ventures/research/R-APIFYGAPS.md), [R-GOVDATA](../../ventures/research/R-GOVDATA.md), [R-LOCAL](../../ventures/research/R-LOCAL.md), [R-RESELLERS](../../ventures/research/R-RESELLERS.md), [R-TRADES](../../ventures/research/R-TRADES.md).

`ventures/FASTEST-MONEY.md` is absent from this base. A provisional copy was read in sibling worktree `gf-A-CASH/ventures/FASTEST-MONEY.md`; it prioritizes closeout, supplied-notice Alabama triage and SAM digests. It is not integrated evidence, an approved price choice, or a new sales assignment. This backlog improves those existing generators and shared delivery reliability; A-CASH retains every sales-material decision. The guide mentions FBA fee-check, but that directory is absent here: do not promise or build an unassigned kit. Other research ideas (rebates, EPA, USPTO, Shopify refunds) remain unvalidated proposals rather than new cards.

No venture is established as publicly live by this planning exercise. Apify payout/pricing/publication, DIBBS registration/quotes/bids, counsel approvals, customer signatures/filings and source permissions stay with their existing owners. Warranty/recall/FDA/carpenter gates are actively assigned. Co-op/freight share the filer/mail/reader/deadline fixes; utility gets a concrete review artifact; CPSC gets source-release protection; property tax gets finite-value validation while V-AUTOMATE retains the broken flow edge. OSHA’s 403 source gate remains the documented owner-download path, assisted by the shared import card; no bypass or fake canary is proposed.

## TODO, failure and skip findings

The repository TODO/FIXME scan found only intentional verification-trap data/test references (`bench/verification/cases/trap-11.yaml` and `bench/verification/test_validate.py`), not actionable product TODOs. Runtime code observations in cards are labeled as such and must be reproduced; they are not claimed exploit or production-failure evidence.

Historical [OWNER-GUIDE-TESTS](../../ventures/OWNER-GUIDE-TESTS.md) describes filer dependency failures and recall wording disagreement. The fresh isolated run below reproduces the filer failure; recall is reserved for RG-RECALL and was not rerun. Earlier installer failures and xfail/xpass counts were not copied forward as current: ventures/tests now passes all 22 checks.

The backend skip scan finds expected OS/symlink/sandbox exclusions, optional sqlite-vector availability, and real-model/CLI prerequisite skips. Those belong to E-PH1/2/4/6/8 rather than new duplicate cards. Public canaries for CPSC/Apify/recall are opt-in; a skipped request supplies no public-source proof. No test was edited or unskipped.

## Verification performed for T-FIND

No product behavior changed, so no separate live-backend walkthrough, customer-account check, network canary or live-worker check was performed. Existing suites below ran locally, one venture directory per pytest process to avoid known import collisions. Those tests may start their own isolated servers or subprocesses. These are fixture/software checks, not live customer evidence.

Command for each row: `~/w/glacier-lean/.venv/bin/python -m pytest -q <test directory> -ra`.

| Test directory | Fresh result |
| --- | --- |
| `ventures/al-bid-triage/tests` | 4 passed in 4.78s |
| `ventures/al-license-verify/tests` | 9 passed in 6.47s |
| `ventures/blocks/connectors/tests` | 18 passed in 10.01s |
| `ventures/blocks/customer/tests` | 10 passed in 78.99s (0:01:18) |
| `ventures/blocks/deadlines/tests` | 6 passed in 1.14s |
| `ventures/blocks/feeds/tests` | 15 passed in 1.21s |
| `ventures/blocks/filer/tests` | 3 failed in 0.53s |
| `ventures/blocks/mail/tests` | 4 passed in 0.12s |
| `ventures/blocks/reader/tests` | 3 passed in 0.05s |
| `ventures/blocks/rules/tests` | 3 passed in 0.04s |
| `ventures/coop-postcards/tests` | 16 passed in 4.12s |
| `ventures/cpsc-prep/tests` | 21 passed, 1 skipped in 0.96s |
| `ventures/dibbs-supply/tests` | 20 passed in 0.83s |
| `ventures/freight-claims/tests` | 35 passed in 307.01s (0:05:07) |
| `ventures/job-closeout/tests` | 3 passed in 4.35s |
| `ventures/osha-filing/tests` | 22 passed in 30.58s |
| `ventures/property-tax/tests` | 9 passed in 12.16s |
| `ventures/sam-amendment-alerts/tests` | 4 passed in 0.10s |
| `ventures/tests` | 22 passed in 0.78s |
| `ventures/utility-audits/tests` | 15 passed in 0.96s |

Additional command: `~/w/glacier-lean/.venv/bin/python -m pytest -q setup/test_health_check.py setup/offline/test_offline.py templates` → **23 passed, 3 failed**. The failures are all in templates/test_templates.py: expected 16 templates but found 20; a node x-coordinate 300 fails the 260 grid assertion; tpl-email-inbox-note lacks its preview pair. B-TEMPLATE-PREVIEWS covers missing artifacts only. Template-set acceptance expectations belong to the independent tester/integrator; layout corrections need a separately scoped template-content owner. Do not delete four templates or weaken assertions to obtain green. B-TEMPLATE-BOUNDARY is additive independent security verification, not permission to rewrite these tests.

From `glacier/web`: `npx tsc -b` failed because TypeScript is not installed in the linked dependency directory (npx printed “This is not the tsc command you are looking for”). `node e2e/theme_lint.mjs` → **passed, 52 files**. `node scripts/check-i18n.mjs --fail` failed with ERR_MODULE_NOT_FOUND for typescript. No dependencies were installed or mutated by T-FIND. The existing environment claim [w89-ui-dependencies](../../vault/claims/2026-10-08-w89-ui-dependencies.md) and filer claim document related prerequisite ownership; their statuses were not changed.

The requested full green baseline is **not** achieved: filer has 3 dependency failures, templates has 3 failures, TypeScript/i18n are blocked, and one CPSC live check skipped. Those are visible handoffs, not failures fixed by planning. Full backend, UI e2e, core test board and live Codex check were not rerun because no behavior/checkpoint was changed and those runs are owned by active engine/UI cards. Temporary raw venture logs: `/tmp/gf-t-find-tests/` (not durable checkpoint evidence).

## Anti-pattern review and handoff

Planning is the explicit T-FIND deliverable, not a substitute for claiming working software. The source review found a risk of stale status/evidence summaries (installer and template counts differ from current files); the correction here is to label historical vs fresh results and avoid changing statuses. All 30 cards tie to a concrete user artifact, source fidelity, approval, recovery or independent proof. No new orchestration layer, new venture, metric exemption, law interpretation or autonomous revenue promise was added.

No change to docs/AMENDMENTS.md or vault claims is authorized by this planning-only file scope. The integrator should record the stale-evidence observation there if it persists after the active wave; lane owners file new reproducible claims before fixes and route the template-count/layout and missing-TypeScript findings to their independent tester/environment owner. Existing claim references are retained, not silently closed.
