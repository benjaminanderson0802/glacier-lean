# C-PH5-PLAN-FIDELITY-TESTER evidence

## Drift check and acceptance first

- Checkpoint: PH5.2, reviewed goal → proposed Environment and acceptance checks. PH3 and PH4 are at their exits; PH5 remains in progress.
- Properties and metrics: P-GOALS, P-VERIFY, P-CONTROL; M-VERIFIED and M-AUDIT.
- Existing tools: the Build API and existing browser e2e harness cover this path. No new planner or test framework was added; the new acceptance test uses those interfaces.
- Acceptance: after editing and approving the goal and checks, the exact goal/spec bytes and acceptance check identities must reach planning and remain visible in the proposed plan before a run. The generated plan must not silently substitute its draft values or model-generated checks. The existing plan edit-feedback path must remain available.

## Results

Command:

```text
/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests/backlog/test_C_reviewed_plan_fidelity.py
```

Result: **1 passed, 1 skipped** (`git diff --check` also passed).

- `test_real_backend_planner_receives_the_reviewed_vision_and_spec` passed against a real uvicorn backend in a fresh temporary `GLACIER_HOME`. The planner prompt contained the reviewed goal and check; the returned plan referenced the exact reviewed vision/spec. The stand-in model deliberately returned a different acceptance check, recorded in [real-backend-api.json](real-backend-api.json), to expose the replacement hazard at the raw API boundary.
- `test_mock_build_screen_displays_the_exact_reviewed_version_before_start` was skipped because the shared `glacier/web/node_modules` symlink has no resolvable Playwright package. The captured import error is in [mock-ui.log](mock-ui.log). No dependency install was attempted because that symlink targets the shared sandbox outside this card's allowed paths.

## Independent finding for the builder

Reading `glacier/web/src/screens/BuildTeams.tsx` shows that approval saves the edited vision/spec before requesting a plan and then overlays those reviewed values into local plan state. The proposed-plan panel currently renders roles, run mode, feature titles, harness data and tasks, but does not render `plan.vision` or `plan.spec`. Therefore it does not visibly establish the approved goal/checks before the “approve and start team” action. The API test also demonstrates why the screen must keep its reviewed-spec overlay: the raw model plan can contain a different acceptance check.

The mock-browser interaction could not be executed in this shared worktree because Playwright is absent. Install/use the existing pinned web dependencies in an isolated test environment, then rerun this test to produce direct browser evidence. No product code or existing acceptance test was edited.

## Anti-pattern review

The relevant risk is a plan that is generated but fails to show the owner's reviewed checks. The test records that risk instead of marking PH5.2 done or changing North Star status. No other North Star anti-pattern was observed in this tester lane.
