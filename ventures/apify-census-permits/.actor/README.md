# Census Building Permits State Change Feed

Compare official monthly Census state residential building permit estimates. Preserve FIPS, reported versus imputed units, valuation units, source vintages, and period changes.

## Input example

```json
{
  "period": "2026-08",
  "previous_period": "2026-07",
  "states": ["01", "22", "28"]
}
```

`period` is a `YYYY-MM` month or `latest`. If omitted, the Actor finds the latest listed monthly release. `previous_period` defaults to the month before the selected period. `states` accepts up to 51 two-digit FIPS strings; an empty list compares all states and DC.

## Output example

Selected fields from a recorded local SDK result on October 11, 2026 UTC. They show values from that run, not a current estimate or an accuracy guarantee.

```json
{
  "record_id": "01:2026-08:2026-07",
  "state_fips": "01",
  "name": "Alabama",
  "outcome": "ok",
  "billable": true,
  "period": "2026-08",
  "previous_period": "2026-07",
  "units": 1731,
  "previous_units": 1560,
  "units_change": 171,
  "units_change_pct": 10.9615,
  "valuation_usd": 451645000,
  "reported_units": 1318,
  "source_url": "https://www2.census.gov/econ/bps/State/st2608c.txt",
  "retrieved_at": "2026-10-11T03:03:37.205932+00:00"
}
```

One dataset row represents one successfully compared state. Values are monthly residential estimates, not individual permit records or addresses. Source thousands of dollars are converted to USD. Reported units are separate from estimates that include imputation. The result includes current and previous source URLs, retrieval dates, and hashes.

## Result meaning and limits

`ok` means both published files were readable and the state values were compared. `uncertain` means a source or row was incomplete, malformed, or changed; its message begins `uncertain - please check`. Missing states and values produce a free uncertain row. This Actor does not currently return a separate `no_match` outcome. A zero previous-period denominator produces a null percentage change. Revisions to a source file can change results between runs.

Uses the [U.S. Census Bureau Building Permits Survey](https://www.census.gov/construction/bps/index.html). The Actor compares monthly state aggregates; it does not provide addresses, permit leads, forecasts, seasonal adjustment, or revision classifications. No accuracy rate or agency endorsement is claimed. Verify important figures against the linked Census files.

## Pricing

The `state-comparison` event costs **$0.002 per successfully compared state**, with platform usage included. Uncertain rows are free; this Actor does not return a separate no-match outcome.

For all 50 states and DC, the maximum event charge per run is **$0.102**. A smaller selected-state list costs up to $0.002 per state compared. Each new run can incur new event charges.
