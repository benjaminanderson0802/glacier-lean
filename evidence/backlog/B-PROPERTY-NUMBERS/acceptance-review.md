# B-PROPERTY-NUMBERS acceptance cases

## Drift check and acceptance, before implementation

- Checkpoint: PH12.17. PH12 depends on PH5 and PH9, both still in progress; the owner-approved PH12 assignment permits this scoped work to start, but this card does not claim a phase exit.
- Defining property and metrics: P-VERIFY; M-FALSE-DONE and M-VERIFIED.
- Existing-tool choice (I-01): use Python's standard `math`/`decimal` parsing and the existing reader; no new dependency or appraisal model.
- Acceptance: invalid monetary/area inputs must produce a deterministic uncertainty tied to their source and must not take part in valuation arithmetic; accepted values and any derived estimate must be finite. Zero and negative monetary/area values are invalid. Correctly grouped formatted numbers remain accepted. Existing self-file guidance remains present.

## Independent evaluator review

An evaluator working from the card's stated requirements, without inspecting product code, independently identified these required cases:

| Input | Required behavior |
| --- | --- |
| `Infinity`, `-Infinity`, `NaN` | Source-linked uncertainty; no valuation arithmetic |
| `1e309` / `1e999999` | Source-linked uncertainty; no overflowed value |
| Huge finite inputs that overflow derived arithmetic | Source-linked uncertainty; omit the invalid estimate |
| Zero and negative amount/area | Source-linked uncertainty; no estimate using the invalid operand |
| Valid formatted amount such as `$1,234,567.89` | Parse to finite numeric value |
| Source path or URL for each rejected document/case field | Retained in the uncertainty |
| Homeowner self-file guide | Remains present |

The review noted that standalone zero semantics and supported formatting need an explicit policy. This card's deterministic policy is: monetary and area values used by this packet must be strictly positive; monetary strings may have an optional leading `$` and valid thousands grouping, while area strings may have valid thousands grouping but no currency symbol. Both may have a decimal fraction. Malformed grouping, other currency symbols, booleans, and non-finite values are rejected.

The independent evaluator confirmed this policy fits the card and does not decide a legal or business matter. Scientific-notation strings such as `"1e6"` are treated as unsupported; a very large positive finite numeric value is accepted only if downstream valuation arithmetic remains finite.

## Pre-fix reproduction

Using synthetic reader fields and a local roll row before changing product code, a notice assessed value of `Infinity` produced `assessment_notice.assessed_value == inf`, `result == "match"`, `status == "ready_for_customer_review"`, and an empty uncertainty list. This reproduces invalid packet output; it is not customer or live-source evidence.

The protected `tests/acceptance/test_v_proptax2.py` covers self-file mode and decision memo content, but has no numeric-input acceptance cases. It remains read-only. Card-specific ordinary unit tests cover the numeric requirements; this evidence preserves the independent evaluator's case matrix without changing a protected check.

## Verification results

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/property-tax/tests/unit/test_B_PROPERTY_NUMBERS.py` — 39 passed.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/property-tax/tests` — 48 passed, including protected self-file acceptance checks.
- Real FastAPI/DBOS fixture run: evidence in [real-backend-run.json](real-backend-run.json); the backend ran a local synthetic command node that imported this venture script, built a packet from synthetic reader fields, and asserted the non-finite notice value caused a source-linked uncertainty. Run completed; packet retained a finite comparable estimate and self-file guide. This is fixture-through-engine proof, not public-source, customer, or production evidence.
- `git diff --check` — passed.

No issue from `anti_patterns_to_detect` was observed: the evidence records an implemented parser/packet change, has passing linked checks, and adds no governance layer or out-of-scope feature. PH12.17 remains unverified as a checkpoint and customer launch remains uncleared.
