# FDIC BankFind Institution Normalizer

Look up FDIC-insured institutions by certificate or state using the official BankFind API. Get normalized records with source dates, data vintage, and bounded pagination.

## Input example

```json
{
  "certificate": "3510"
}
```

Provide a certificate number (kept as a string) or a two-letter state code. You may provide both to narrow the query. `max_records` defaults to 100 and is capped at 1,000; `page_size` controls requests from 1 to 100. `active_only` defaults to `false` and preserves the source's literal active flag.

## Output example

Selected fields from a recorded local SDK result on October 11, 2026 UTC. The FDIC may update records after this run; the sample is not a current status guarantee.

```json
{
  "record_id": "3510",
  "outcome": "ok",
  "billable": true,
  "message": "Official institution record; not a bank safety or deposit coverage determination.",
  "certificate": "3510",
  "name": "Bank of America, National Association",
  "active": true,
  "state": "NC",
  "city": "Charlotte",
  "postal_code": "28202",
  "source_updated_at": "2026-06-29",
  "source_vintage": "institutions_20261009090008",
  "source_total": 1,
  "truncated": false,
  "record_url": "https://banks.data.fdic.gov/bankfind-suite/bankfind/details/3510",
  "retrieved_at": "2026-10-11T03:03:36.085759+00:00"
}
```

Each returned institution is one dataset row. The output preserves the FDIC certificate, literal active status, source record date, source vintage, retrieval time, and source hash. The record date and retrieval time describe different things.

## Result meaning and limits

`ok` means the requested official snapshot returned a validated institution record. `no_match` means the official snapshot returned zero records; its message names the source and retrieval date, and it is free. `uncertain` means the source, page sequence, or response did not support a complete result; its message begins `uncertain - please check` and it is free. If results exceed `max_records`, rows include `truncated: true`; narrow the filter before treating the list as complete.

Uses the [FDIC BankFind API](https://api.fdic.gov/banks/docs). This Actor returns institution-directory fields only. It does not assess solvency, bank safety, deposit coverage, branches, or financial performance. Optional source fields may be absent. No accuracy rate or agency endorsement is claimed; verify important information with the FDIC.

## Pricing

The proposed event is `bank-record` at **$0.002 per returned institution**. No-match and uncertain rows are free. The Store pricing panel controls actual charges. Platform usage should be included, and automatic Actor-start and dataset-item events should be disabled. Set a maximum run charge in Console before use; `pricing.json` is only a reference.

At the 1,000-record input cap, event charges total at most $2.00. A run may still incur platform compute costs. The Actor writes each result before charging and stops when its configured event limit is reached.
