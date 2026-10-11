# Ready venture automations

From the owner's existing source install, with Glacier running on port 8766, run this **one PowerShell line**:

```powershell
Set-Location "$env:USERPROFILE\glacier-dev"; $env:GLACIER_HOME = "$env:USERPROFILE\.glacier-dev"; & .\.venv\Scripts\python.exe .\ventures\install_all.py --ready --start --api http://127.0.0.1:8766
```

This uses the existing project venv and Git for Windows Bash. It reads the install token from that Glacier home; no token needs copying into the command. Change the checkout, home, and port together if using a different installation. Keep Glacier running in the background; start-at-logon setup remains the existing platform/owner step. Installing venture schedules does not install or restart the desktop application.

`--ready` selects manifests whose status is exactly `ready`. At this revision that means Co-op Postcards, Freight Claims, Job Closeout, OSHA Filing, and Utility Audits: 16 business flows and five health canaries. Draft, blocked, on-hold, and status-less ventures are excluded. The legacy installer invocation without `--ready` retains its all-manifest behavior.

The installer validates the complete selection before registering flows. Existing declared schedules remain intact. Other ready flows receive a daily 07:00 UTC DBOS schedule, with one catch-up after downtime and overlapping runs skipped. A waiting approval counts as an active run, so tomorrow's schedule does not create another copy while the owner is reviewing it. Each venture also gets an hourly health canary at five minutes past the hour.

`--start` starts each flow immediately unless it is paused or already queued, running, or waiting. Missing customer files or connector setup can produce a failed run with an actionable command error. Provide the requested input or complete the existing owner step and rerun that flow in Glacier. Installation never seeds synthetic customer records in the owner's home. Reinstallation updates changed definitions, avoids unnecessary vault revisions, and preserves a saved owner pause. Do not run concurrent installer processes against the same home.

## Inputs and owner steps

Customer confirmation, signatures, filings, customer delivery, first listings, and billing decisions remain owner/customer steps. Existing approval nodes remain in place. Additional schedules do not approve them.

- Co-op claims can read a supplied local Jobber-shaped export at `ventures/coop-postcards/intake/jobber.json` under `GLACIER_HOME`, otherwise they use the existing read-only connector. The export mode is labeled `fixture` by the upstream CLI; review its provenance before using the draft.
- Job Closeout can read a supplied versioned Jobber response at `ventures/job-closeout/incoming/jobber.json`, otherwise it uses authorized read-only Jobber access. It writes local Markdown/PDF packets, then waits for review. The local-input CLI also labels its mode `fixture`.
- Freight uses its existing incoming CSV fallback and local claim, receipt, signer, and recovery inputs. The settlement review note is separate from the customer's settlement JSON.
- OSHA outreach first uses an owner-downloaded official Summary Data CSV at `ventures/osha-filing/incoming/summary.csv` when present, otherwise the existing public feed. Proof files stay inside the Glacier home. Customer certification/submission is unchanged.
- Utility calculations retain the launch-state and customer-record approvals. Scheduling does not choose the launch state or enable billing.

## Health and failures

The canaries inspect the installed schedules and latest run records through Glacier's authenticated local API. Missing schedules, failed latest runs, overdue scheduled starts (two-hour grace), and runs queued/running for over 24 hours cause a failed canary. Owner pauses and waiting approvals are reported explicitly. A successful canary writes a readable report to Memory under `ventures/<slug>/health/`.

Failed runs are recorded in the Glacier run history and should appear in the Home `needs_you` list. However, the latest Linux proof produced a failed canary run but did not find that run in `GET /api/home`. Treat Home alert visibility as unverified until the backend/Home lane resolves this. No external notification service or paid account is added. The canary measures **local automation health**, not government-source freshness, legal correctness, customer readiness, or successful real-world filings. Glacier must be running for its canaries and screen alerts to run. A fully stopped engine cannot report its own outage.

## Linux proof and checks

Validation only (does not contact an engine or execute commands):

```sh
~/w/glacier-lean/.venv/bin/python ventures/install_all.py --ready --dry-run
```

Real disposable backend smoke proof:

```sh
~/w/glacier-lean/.venv/bin/python ventures/install_all.py --prove /tmp/v-automate-proof
```

The proof creates a fresh `/tmp/glacier-venture-proof-*` home and starts its own real FastAPI/DBOS process on a free loopback port. It installs twice, starts every ready flow, and records each node state, unchanged-install result, acceptance result when executed, and steps left behind owner gates. It copies only clearly synthetic local fixtures into that disposable home, never the owner's home. It makes no approval decisions. A deliberate schedule removal then exercises the real canary failure and Home alert path. The backend is stopped on exit; the isolated home and proof files remain available for inspection.

A `waiting` result proves the owner boundary was reached; it does **not** prove later commands or acceptance checks passed. The proof is operational smoke evidence, not an independent acceptance check. Existing tester-owned suites and flow acceptance definitions were not changed. Windows command binding is tested on Linux; the owner PC execution of this revision remains an owner step.

## Drift check and scope

Benjamin Anderson's V-AUTOMATE card (2026-10-10) authorizes this work. It advances PH12.3 and PH12.22, serving P-LOOPS/P-CONTROL and M-SURVIVE/M-INTERVENE. PH5 and PH9 have supporting checkpoint evidence but remain marked in progress; this card is explicitly parallel-safe and does not mark a checkpoint done.

Existing free/open-source Glacier, DBOS, Python, and git cover scheduling, persistence, audit, and alerts. This change only connects ready venture definitions to those capabilities; it introduces no scheduler or notification framework and no dependencies or spending.

Acceptance named before implementation: existing installer/idempotence/Windows-binding tests, existing ready-venture suites, real engine install twice, start every ready flow, and observe an injected canary failure inside Glacier. Ordinary unit tests were added for new installer glue; independent acceptance files remain untouched.

The anti-pattern review found that the prior `--dry-run` was validation-only and Job Closeout's descriptive flow was not executable by Glacier. The new proof distinguishes actual completion from unexecuted owner-gated work, and Job Closeout now uses the runtime node/edge contract. Evidence is kept here to respect the card's strict path scope; NORTHSTAR, AMENDMENTS, vault claims, manifests, and test-board files were not edited.
