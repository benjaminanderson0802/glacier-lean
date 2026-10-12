---
id: CLM-2026-10-11-CL-QUALITY-VALIDATION
filed_by: CL-QUALITY
run_id: local-builder
node_id: CL-QUALITY
checkpoint: PH12.22
kind: environment
summary: Independent fixture migration and missing web TypeScript prevent a green full board
status: open
assigned_to: integrator-and-independent-tester
attempts_made: 1
resolution: null
resolution_evidence: null
evidence: [evidence/quality-venture-tests.log, evidence/quality-tsc.log, evidence/quality-i18n.log]
---

This scoped handoff is kept inside the card's authorized `ventures/whop-clipping` paths. Integrator should register it under `vault/claims/`; that root path is outside this card's file list.

The new mandatory FFmpeg gate intentionally rejects legacy `b"fixture"`, `b"master"`, and `b"untouched source bytes"` media, although the older tests monkeypatch `_ffprobe` to report dimensions and acceptable loudness. New generated-fixture tests prove valid media is stocked and uploaded through the recording adapter. Independent tester should replace fake-media fixtures with generated valid captioned media or stub the new gate in pure scheduling tests, retaining meaningful assertions; builder did not edit those tests. The two-hour default assertion also needs the owner's explicit 150-minute requirement, or an explicit two-hour legacy configuration when testing backward compatibility.

Affected unchanged tests:

- `test_multi_campaigns.py::test_producer_marks_ffprobe_error_as_clip_qa_failure_and_continues`
- `test_multi_campaigns.py::test_producer_stocks_each_qa_passing_clip_before_rendering_next`
- `test_pipeline.py::test_live_cycle_requires_explicit_config_and_records_side_effects`
- `test_pipeline.py::test_dry_run_reservation_can_be_reused_live_on_same_channel`
- `test_schedule.py::test_distributor_uses_nearest_deadline_and_manual_submit_queue`
- `test_schedule.py::test_producer_stocks_library_and_distributor_queues_whop_manually`
- `test_schedule.py::test_distributor_respects_two_hour_spacing_and_six_per_day_cap`

The environment maintainer should restore pinned web dependencies in the shared sandbox, then rerun `npx tsc -b` and `node scripts/check-i18n.mjs --fail`. No card code can supply the missing TypeScript package. The core script also assumes ownership of shared temporary paths and a fixed server port; use the integrator's controlled test sandbox for that board.

Until these checks pass, do not mark CL-QUALITY or PH12.22 independently verified/done.
