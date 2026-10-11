# SAM amendment and deadline alerts

## What it does

This local prototype watches SAM.gov Contract Opportunities for industrial supplies merchant wholesalers (NAICS 423840, one of Benjamin's registered trades). Given two saved Opportunities API v2 response snapshots, it filters by NAICS and reports newly observed notices, version changes, and response-deadline changes in a dated Markdown digest. Each event carries its official notice URL. It does not infer eligibility, predict awards, or recover amendment history from before the first snapshot.

The government data is free. SAM.gov already has search and follow tools, so the paid hypothesis is the simple, dated change digest for a narrow trade. A buyer pays only if the focused workflow saves monitoring time or helps them notice a changed deadline. Willingness to pay is unproven.

The SAM Data Services page was reachable as an HTML application, but no direct keyless daily CSV extract URL could be accessed from this worktree. The sample is therefore generated from explicitly illustrative fixtures shaped like the documented Opportunities API v2 response. It is not a real SAM.gov opportunity or live-source canary. Live API use requires the owner's own `sam_api_key`; confirm the current official terms and limits before polling.

## Who pays and price hypothesis

Small industrial-supply wholesalers and procurement teams that bid federal opportunities are the intended buyers. The validation offer is a four-week pilot for **$49**, covering one NAICS watch. If buyers continue after the pilot, the hypothesis is **$29/month**. Both prices are tests, not market findings, and nothing is charged until Benjamin offers and approves it.

The three prospect rows link to first-party business contact pages. They are manual research leads, not SBA profile records, endorsements, proof of current registration, NAICS fit, active bidding, or consent. Check the linked contact route and confirm fit directly before any invitation. Use one individually reviewed invitation at a time; do not bulk mail or automate outreach.

## One owner step

1. Choose one prospect, check its linked business contact page and contact route, personalize the greeting, fill in the valid business postal address, review the offer and sample, then send the one pitch email in [PILOT.md](PILOT.md) yourself.

The API key is only needed if a paid pilot is accepted and live monitoring is activated. The owner then obtains the free key from SAM.gov and stores it in Glacier Secrets as `sam_api_key`. Never put it in a file or command line. No account signup, email sending, billing, payment, signature, bid, or agency submission is automated.

## Use the prototype

```sh
~/w/glacier-lean/.venv/bin/python ventures/sam-amendment-alerts/scripts/digest.py \
  --before ventures/sam-amendment-alerts/tests/fixtures/snapshot-2026-10-09.json \
  --after ventures/sam-amendment-alerts/tests/fixtures/snapshot-2026-10-10.json \
  --naics 423840 \
  --output /tmp/sam-amendment-digest.md
```

The snapshots must be saved SAM.gov Opportunities API v2 JSON response objects (`opportunitiesData` envelope), with `retrieved_at` and `source_url` added by the local snapshot step. The included manual Glacier flow compares `$GLACIER_HOME/ventures/sam-amendment-alerts/incoming/before.json` and `after.json` and writes a local draft. It does not fetch or email data; live API snapshot capture remains unimplemented in this pilot kit.

## Drift check and acceptance

- **Checkpoint:** PH12.5, government data feeds + deadline tracker; the pilot kit also contributes to PH12.22 integration. No North Star checkpoint status is changed here.
- **Dependencies:** PH12 depends on PH5 and PH9, both recorded `in_progress`. The PH12 wave rules allow an assigned card to start before dependencies exit; therefore this card may be built, but PH12.5 cannot be marked done.
- **Properties and metric:** P-LOOPS (repeatable snapshot checks), P-VERIFY (source/date evidence), P-CONTROL (human owns outbound pitch and consequential actions), and P-USABLE (one clear owner step). M-COST remains visible as an operating measure; no revenue is claimed.
- **Existing tool / I-01:** SAM.gov's own search and follow features are free substitutes. The narrow custom glue is justified only to compare saved snapshots and format source-linked diffs; this does not repackage exclusive data or replace SAM.gov.
- **Acceptance test / I-03:** `tests/test_digest.py` checks the documented API v2 envelope, a changed version plus deadline, a new notice, unchanged/out-of-scope filtering, source/date provenance, and the no-match result. The sample's metadata identifies it as fixture generated.

## Known limits

- A notice absent from the next response is not treated as a cancellation; this prototype only reports new notices and explicit version/deadline differences.
- The official API's current-version behavior means no pre-enrollment amendment history is promised.
- A missed or stale alert could matter. Confirm the live notice and its response deadline directly on SAM.gov.
- This is not legal or procurement eligibility advice, an award forecast, a bid writer, or an official government service.
