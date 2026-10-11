# B-DIBBS-INTAKE independent acceptance criteria

Frozen by an independent evaluator from the card specification before implementation.

## Synthetic baseline

- DIBBS detail and supplier quote artifacts have fixed content, SHA-256 hashes, and acquisition dates.
- A ranked row describes part `P-100`, quantity `10`, supplier `S-1`, and quote revision `R1`.
- Explicit owner confirmations bind the exact DIBBS detail and quote records.
- The matching records contain the existing facts needed to prepare an unsigned CSV.

## Pass observations

- Every ranked row identifies the immutable source hashes and acquisition dates for both inputs.
- The row traces to the owner-confirmed DIBBS detail and supplier quote records.
- Matching synthetic records produce an unsigned CSV whose rows can be traced to the supplied inputs.

## Mutations

Starting from the confirmed baseline, change one field at a time: part, quantity, supplier, or quote revision. The old confirmation must not be reused. The changed row must be withheld or require a new confirmation. This evaluator does not judge procurement eligibility.

## Fail observations

- A ranked row lacks a source hash or acquisition date, or cites a source that does not match the supplied immutable content.
- A ranked row lacks traceability to the owner-confirmed detail or quote.
- Any single-field mutation inherits the baseline confirmation.
- A generated CSV is signed or its rows cannot be traced to the supplied inputs.
