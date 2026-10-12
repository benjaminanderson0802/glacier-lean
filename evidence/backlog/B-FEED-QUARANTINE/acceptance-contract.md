# B-FEED-QUARANTINE independent acceptance contract

## Purpose and independence

This is the independent evaluator's frozen, spec-only contract for PH12.5, card B-FEED-QUARANTINE. It defines observable behavior without depending on implementation details. The evaluator must use a fresh context and judge the candidate through the supported feed interface and query surface. The builder must not edit, disable, or bypass this contract or the evaluator's check.

This case uses synthetic, local data only. It makes no live-source, production-data, or phase-exit claim. It serves P-VERIFY and P-LOOPS and supports M-FALSE-DONE and M-SURVIVE.

## Test fixture

Use an isolated disposable store and one synthetic source. Define:

- Trusted snapshot **R1**: a small, fixed set of uniquely identifiable rows.
- Validated schema **S1**: the exact required field set remembered when R1 is accepted.
- A configured canary identifier present in R1.
- A source-reported total that equals the count of the valid candidate rows.

First import R1 through the supported interface. Query the source and record the exact R1 rows and S1. Reopen the isolated store and confirm those same rows and S1 remain available before starting each suspect-candidate case. Reset to this baseline for each case so one rejection cannot affect another.

The evaluator may use whatever candidate fixture and stable observable query/API the supported interface permits. Do not rely on private implementation state. Compare rows as complete records, including identifiers and field values; row order may be ignored only if the feed contract defines results as unordered.

## Required rejection cases

For each case below, submit the suspect candidate as a refresh from the R1/S1 baseline. The other validity checks must pass, so the named defect is isolated.

1. **Source-count mismatch greater than 1%**: report 100 source records while supplying 98 candidate records. Keep the canary and S1 fields present. Since 2% is above the threshold, the refresh must be rejected.
2. **Missing canary**: supply a complete-count candidate with S1 fields, but omit the configured canary identifier.
3. **Required schema field removed**: supply a complete-count candidate containing the canary, but remove one required field present in S1 from the candidate schema/records.

For every rejection, assert all of the following:

- The refresh result visibly reports failure/quarantine and identifies that the candidate was not trusted. A generic successful refresh result is a failure.
- A subsequent query returns exactly R1; none of the suspect candidate rows are exposed as the trusted snapshot.
- The remembered validated schema is still exactly S1; it has not been replaced by the suspect candidate schema.
- After closing and reopening the isolated store, the query still returns exactly R1 and the remembered validated schema is still S1.
- If the public result includes a `changed` indicator, it reports no trusted-snapshot change for this rejected candidate.

## Valid replacement and atomicity

Starting again from R1/S1, submit a valid replacement **R2** with different, uniquely identifiable rows, a complete matching source count, the configured canary, and the same required field set S1. Assert that the refresh succeeds and the query returns exactly R2; after reopening the store, R2 remains queryable and S1 remains the validated schema.

Also verify atomicity at the observable boundary. While the replacement is being promoted, make repeated independent queries to the supported read surface. Every observation must be the complete old pair (R1, S1) or the complete new pair (R2, S1); no query may return partial/mixed rows or a schema inconsistent with the rows. Where the supported test harness permits a write failure or process interruption during promotion, inject it once and assert that reopening yields the complete old pair (R1, S1), never a partial candidate. Record which atomicity path was exercised; a normal successful refresh alone does not prove rollback on interrupted promotion.

## First-import failure distinction

Use a separate empty disposable store with no trusted snapshot or remembered schema. Submit an invalid first candidate (use the missing-canary case). Assert that:

- The refresh result reports failure and clearly indicates that no trusted snapshot exists to retain.
- A query returns no trusted rows, and there is no remembered validated schema.
- The result is distinguishable from the rejection result with R1/S1 present, which must report failure while retaining the previous snapshot.

The exact user-facing wording is implementation-defined; the distinction in state and result must be observable and unambiguous.

## Pass criteria and evidence

The contract passes only when all three suspect-candidate cases preserve R1/S1, the valid replacement exposes only complete trusted state and survives reopen, and first-import failure is distinguishable from failure with a retained snapshot. Any failed assertion fails the acceptance case; do not weaken or skip a case to match implementation behavior.

The evaluator's result must identify the source revision, isolated fixture setup, each case outcome, reopen checks, and which atomicity path was exercised. Label this as synthetic fixture-through-interface evidence. Do not describe it as a live public-source check or a PH12.5 exit. The builder's ordinary unit tests are supplemental and do not replace this independent evaluation.
