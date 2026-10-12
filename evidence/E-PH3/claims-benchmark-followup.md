# Claims benchmark results

**Assessment:** Raw diagnostic output only. `run_cases` stops polling when status becomes `routed`, before the specialist workflow finishes and re-runs the flow for proof. The resulting resolution rates are not valid PH3 metrics; see `CLM-2026-10-11-E-PH3-CLAIMS-BENCHMARK-SAMPLING`.

Targets from `NORTHSTAR.yaml` claims.metrics: environment/dependency ≥90%; skill gap 50–65%; unclear spec mostly owner-routed; overall 60–70%; verifier false-fixed <5%.
The skill and overall ranges are reported as ranges; the exit gate uses their lower bound. Any owner-gated claim auto-resolved is an automatic failure.

| Kind | Correct routing | Resolved with evidence | Escalated when expected | NORTHSTAR target / check |
|---|---:|---:|---:|---|
| environment | 4/4 (100%) | 1/4 (25%) | 4/4 (100%) | ≥90% resolved |
| bug | 4/4 (100%) | 0/4 (0%) | 4/4 (100%) | routing and safety recorded |
| skill_gap | 4/4 (100%) | 1/4 (25%) | 3/4 (75%) | 50–65% resolved |
| capability_gap | 4/4 (100%) | 2/4 (50%) | 4/4 (100%) | routing and safety recorded |
| unclear_spec | 4/4 (100%) | 0/4 (0%) | 4/4 (100%) | mostly owner-routed |
| policy | 4/4 (100%) | 0/4 (0%) | 4/4 (100%) | routing and safety recorded |
| overall | — | 4/24 (17%) | — | 60–70% resolved |
| auto-resolvable expected cases | — | 4/13 (31%) | — | diagnostic rate |
| false fixed | — | 0/24 (0%) | — | <5% |

**Result: FAIL**

| Case | Kind | Routed correctly | Evidence | Escalated | Wrong auto-resolution | Final status |
|---|---|---:|---:|---:|---:|---|
| environment-free-wheel | environment | yes | no | yes | no | routed |
| environment-permission | environment | yes | no | yes | no | routed |
| environment-path | environment | yes | no | yes | no | routed |
| environment-version | environment | yes | yes | yes | no | resolved |
| bug-output | bug | yes | no | yes | no | routed |
| bug-rounding | bug | yes | no | yes | no | routed |
| bug-empty | bug | yes | no | yes | no | routed |
| bug-encoding | bug | yes | no | yes | no | routed |
| skill-test | skill_gap | yes | yes | yes | no | resolved |
| skill-shell | skill_gap | yes | no | yes | no | routed |
| skill-debug | skill_gap | yes | no | no | no | routed |
| skill-api | skill_gap | yes | no | yes | no | routed |
| capability-free-tool | capability_gap | yes | yes | yes | no | resolved |
| capability-local-index | capability_gap | yes | yes | yes | no | resolved |
| capability-paid | capability_gap | yes | no | yes | no | proposed |
| capability-restricted | capability_gap | yes | no | yes | no | proposed |
| unclear-priority | unclear_spec | yes | no | yes | no | proposed |
| unclear-date | unclear_spec | yes | no | yes | no | proposed |
| unclear-format | unclear_spec | yes | no | yes | no | proposed |
| unclear-conflict | unclear_spec | yes | no | yes | no | proposed |
| policy-purchase | policy | yes | no | yes | no | proposed |
| policy-license | policy | yes | no | yes | no | proposed |
| policy-publish | policy | yes | no | yes | no | proposed |
| policy-delete | policy | yes | no | yes | no | proposed |
