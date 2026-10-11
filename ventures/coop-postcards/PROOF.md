# Verification proof — V-COOP2

Venture release status: **ready for owner setup and review**. The PH12.13 roadmap checkpoint remains `todo` in NORTHSTAR because PH5 and PH9 are still in progress; this card does not mark a roadmap checkpoint done. The live account check below used only fixture data because the Jobber credentials are unavailable in this sandbox.

## Drift check

- Checkpoint: PH12.13, Co-op claims + street postcards.
- Dependencies: PH5 and PH9 are not at exit. The owner-approved PH12 wave authorizes this venture work to start, but this card does not mark PH12.13 done.
- Property and metric: P-CONTROL for review-only approvals and no unapproved external action; P-VERIFY and M-VERIFIED for evidence-gated drafts and source-linked checks.
- Existing tools: the shared read-only Jobber connector, shared rules checker, deadline tracker, and mail helpers cover connector/rules/deadline/rendering needs. Venture-specific code is glue for claim records, privacy filtering, and EDDM review dimensions (I-01).
- Acceptance: `ventures/coop-postcards/tests/acceptance/test_v_coop2.py`; it was not edited. The required fixture and source checks pass. The independent compact-input check still disputes `filing_ready=True` despite missing evidence and unverified program terms; this remains recorded in `DISPUTE.md` and is a safe not-ready result.

## Tests and source checks

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/coop-postcards -q
```

Result: **16 passed**. This includes the existing acceptance suite and two new non-acceptance tests for the metadata-only Jobber query and the EDDM review PDF page size. Acceptance files and `ACCEPTANCE.md` were not changed.

On 2026-10-10, all five configured brand source URLs returned HTTP 200: Carrier, Trane, Lennox, Rheem, and Goodman. They remain `unverified`: public pages verify that source pointers resolve, not dealer enrollment, account-specific eligibility, evidence rules, funding, or deadlines. Trane points dealers to its secure portal; Lennox directs dealers to a guidebook for full program details; Goodman’s 2025 APlus guide remains historical. The source and check results are in `evidence/eddm-usps-benchmark.json`.

The official USPS EDDM Retail checker, DMM 143, EDDM Quick Service Guide 140, and DMM 101 pages returned HTTP 200. The benchmark follows the EDDM-specific Quick Service Guide minimum: flat mailpiece; 3.3 oz maximum; length 5–15 in; height 3.5–12 in and no greater than length; thickness 0.007–0.75 in; and at least one qualifying dimension strictly greater than 10.5 in length, 6.125 in height, or 0.25 in thickness. The online checker screen shows a generic 3.5-inch minimum length, while the EDDM-specific guide says 5 inches; the validator uses the specific guide’s 5-inch minimum. The fixture’s 11.5 × 6.25 × 0.01 in, 3.3 oz piece passes; equality at all three qualifying thresholds, a 4.99-inch length, and a 3.31 oz weight fail.

## Real local Glacier engine runs

Both manifest flows were installed in a disposable `GLACIER_HOME` and run through the real local FastAPI/DBOS engine. The command nodes ran using the project interpreter. Fixture-only approvals were recorded to exercise review nodes; they are not owner approval of any real claim or postcard.

- `coop-claim-readiness`, run **`1f4d0b2bae3b`**: all four nodes completed. The fixture produced one Carrier Markdown/JSON/PDF draft for job 2048, with `rule_status: unverified`, `filing_ready: false`, and no external action. The review node recorded local draft review only; `record_review_only` reported that the dealer must sign and file directly.
- `street-postcard-proof`, run **`7f7b4ed360a9`**: all five nodes completed. The synthetic route passed sender, suppression, and USPS size/weight checks; address verification remained uncertain because the fixture has no city/state/ZIP. The proof node wrote HTML and a two-sided EDDM review PDF at 11.5 × 6.25 inches. The shared mail helper also wrote its separate 6 × 4 local test proof; it did not request Lob because no Lob test key was configured. No API call, mail order, payment, publication, or mailing occurred.

The run IDs, node states, stdout outputs, and errors are captured in `evidence/live-flow-runs.json`. Copied claim artifacts and the EDDM HTML/PDF output are under `evidence/live-flow-output/`. The EDDM PDF’s two page boxes are 828 × 450 points, and its metadata and size-boundary outcomes are captured in `evidence/eddm-usps-benchmark.json`. It is a review proof, not a production print master: no USPS indicia, bleed, paper stock, color profile, or final press setup is included.

## Live Jobber limit and one-command owner check

The four Jobber OAuth secret names are unavailable in this sandbox, so no live account request was made. The real engine run used `fixtures/jobber_completed_job.json`. The claim intake now calls the shared `JobberClient` GraphQL path with only job ID/number, title/status, completion time, and source URL fields; the query does not request client, property, or custom-field data. The new test asserts those fields are absent.

After the connected Jobber test app’s four OAuth values are saved in Glacier Settings → Secrets, the owner can run this one command from the repository root to exercise live, read-only intake and write local drafts:

```sh
~/w/glacier-lean/.venv/bin/python ventures/coop-postcards/scripts/generate_claim_drafts.py
```

## Owner-only step

Connect the read-only Jobber test app; confirm current brand eligibility, terms and deadlines; authorize, sign and file claims; choose any price or campaign budget; and approve the exact postcard proof before arranging a USPS EDDM mailing. These actions remain manual. No live customer data, claim filing, account creation, price choice, purchase, publication, or mailing was performed.

## Findings

A previous note said Jobber intake did not request homeowner/client fields, but the shared connector’s general `get_jobs()` query did request them. This venture now uses a metadata-only query through the same shared client; a focused test verifies it. A previous note also identified the shared mail PDF as 6 × 4 inches; the venture now creates a separate 11.5 × 6.25 inch EDDM review PDF and keeps the shared 6 × 4 test output clearly separate. No acceptance check was weakened or changed.
