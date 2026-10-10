# OSHA filing preparation progress

## Drift check

1. Checkpoint: PH12.16, OSHA filing.
2. Dependencies: PH5 and PH9 have not reached their exits. PH12 is owner-approved and this card explicitly authorizes work in wave 6, so this card can start; it cannot mark PH12 or its exits complete.
3. Defining properties and metrics: P-CONTROL / M-VERIFIED for customer review, customer-held certification/submission, and approval-gated outreach; P-VERIFY / M-VERIFIED for cited rules and deterministic totals; P-USABLE / M-INTERVENE for the short owner-step list.
4. Existing tools: the OSHA public feed, mail, rules, filer, deadlines, customer, and Jobber connector blocks are present. This venture composes those interfaces; no duplicate shared block or new dependency is needed.
5. Acceptance test, written first: `ventures/osha-filing/tests/test_osha_filing.py` covers arithmetic and hours checks, missing evidence as uncertain, shared Jan 2–Mar 2 deadlines, conservative feed prospecting, local-only filer use, and flow gates with customer-only certification/submission.

Implemented a customer-reviewed Form 300A draft, OSHA feed prospect selection, render-only postcard and distinct landing-page preparation, Jobber read-only preview, and shared deadline reminders. The customer must certify, sign, post, and submit. No live outreach or OSHA portal access is enabled.

Focused acceptance tests pass (6 passed); all four manifest flows validate; the official OSHA feed parses 400,288 rows with no alerts; a real-data postcard preview created a PDF proof and distinct page in render-only mode; and a synthetic zero-injury input produced a cited Form 300A draft with `match`. The required `heavy npm run live` attempt started the backend but Vite failed because this worktree's installed `node_modules` lacks `vite/bin/vite.js`. Dependency setup is outside this venture's file lane. The real Glacier run and screenshot remain pending; this card does not change NORTHSTAR checkpoint status.
