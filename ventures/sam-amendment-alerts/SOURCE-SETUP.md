# Set up SAM.gov snapshot collection

The collector reads SAM.gov Contract Opportunities API v2 using the selected
NAICS code or codes. It is read-only. It saves a snapshot only after every
result page has been retrieved and checked. The digest still compares saved
snapshots; this command does not schedule polling, email alerts, or reconstruct
amendments from before the first snapshot.

## Add the API key

1. Obtain your own SAM.gov public API key through the official SAM.gov process.
2. In Glacier, open **Settings → Secrets** and save the key under the name
   `sam_api_key`.
3. Do not paste the key into a flow, command, chat, file, or snapshot. The
   collector reads it from Glacier Secrets when it runs.

If the key is missing, the collector stops before making a request and tells
you to save `sam_api_key` in Glacier Settings → Secrets, then retry.

## Collect a snapshot

From the Glacier project root, choose one or more NAICS codes and an output
path. For the pilot's 423840 watch:

```sh
snapshot_home="${GLACIER_HOME:-$PWD/data}"
~/w/glacier-lean/.venv/bin/python ventures/sam-amendment-alerts/scripts/collect_snapshot.py \
  --naics 423840 \
  --output "$snapshot_home/ventures/sam-amendment-alerts/incoming/after.json"
```

Repeat `--naics` to include additional codes. Choose a new output filename for
each collection so the earlier comparison snapshot remains available. Run the
existing digest command with the two saved snapshots after reviewing that both
were collected successfully.

The collector requests up to 100 records per page, at most 20 pages and 2,000
records by default. These are safety bounds, not a promise that a query fits
within them. If the API reports more results than the configured bounds, a page
is missing or malformed, or SAM.gov returns a quota/rate-limit error, the run
fails and does not write a new complete snapshot. Wait and retry after a quota
response; if a result exceeds the page or record bound, narrow the selected
NAICS scope or have the implementation's bounds reviewed before rerunning.

## Check the saved file

A successful JSON file contains the SAM `opportunitiesData` response records
plus local metadata: selected NAICS codes, UTC retrieval timestamp and date,
the credential-free official API endpoint, page count, record count and an
explicit `complete` status. API keys are not included in the URL, metadata,
records, or error messages. The file contains only the latest records returned
by the API; it cannot provide history from before the first saved snapshot.

Before routine polling, confirm the current official API terms and rate limits.
Fixture tests do not prove live API access. A live read is only available when
the owner has already configured the free key in Glacier Secrets.
