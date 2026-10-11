# Alabama contractor roster verifier

This is a small Apify Actor prototype for matching a contractor license number or business name against a dated Alabama contractor roster CSV. It returns the literal status and expiration fields when the supplied file has them, a dated `no match found` when it does not, and `uncertain — please check` for stale or ambiguous inputs. It never calls the Alabama board, opens a browser, or treats roster absence as proof that a business is unlicensed.

## Who may pay and price hypothesis

Potential buyers are municipal purchasing/public works teams, property managers, and general contractors that repeatedly check subcontractors. The first test is a **$49 paid pilot** for one customer-supplied, authorized roster and up to 100 exact checks. A later self-serve hypothesis is **$0.05 per completed lookup**, with a $5 per-run cap. Neither price is validated; the prospect email asks whether this workflow is useful before any listing is published.

## Source and permission boundary

The Alabama Licensing Board for General Contractors points consumers to its license search. Its public detail pages warn that the displayed database may be incomplete and is **not official**; the research file also bars automated access unless the board permits it. The board's law describes an annual roster containing contractor names and places of business, but the currently visible board site does not provide a confirmed downloadable machine-readable roster. See the [board](https://genconbd.alabama.gov/), [board search page](https://genconbd.alabama.gov/search/), and [Section 34-8-26](https://genconbd.alabama.gov/Law/34-8-26.pdf).

For that reason, this version only reads a CSV explicitly uploaded by the Actor user. Apify's `fileupload` field supports user-uploaded files; the runtime restricts network retrieval to Apify file storage. `source_url` is metadata and is never fetched. Before commercial reuse of a board export, Benjamin must ask the board if a downloadable export exists and whether automated use, commercial redistribution, and status/expiry fields are permitted. Until permission is clear, only use an export that the buyer provides and is authorized to use. See the board's public-search disclaimer and the cautions in [`R-APIFYGAPS.md`](../research/R-APIFYGAPS.md).

The roster is a snapshot, not real-time status. A name match is exact after basic punctuation/case normalization; it is not proof of identity. Results do not establish legal qualification, insurance, workmanship, or endorsements. If a file has no status/expiration columns, those fields remain blank.

## Run locally

```sh
cd ventures/al-license-verify
~/w/glacier-lean/.venv/bin/python -m pytest -q tests
```

For an Apify run, upload an authorized UTF-8 CSV using the `roster_file` input, enter the file's official source URL and as-of date, then add one or more exact lookup objects:

```json
[{"license_number":"AL-EXAMPLE-1042"},{"name":"Example Building Services LLC"}]
```

Accepted CSV headers include common variants of license number, company/name, status, expiration date, specialty, address, city, state, and ZIP. The Actor accepts at most 100 lookups and a 25 MiB CSV. A snapshot older than 365 days is always uncertain. No credentials or API key are needed.

## Files

- `scripts/verify.py`: CSV parsing, exact match, date handling, host restriction, and output vocabulary.
- `src/__main__.py`: Apify Actor wrapper.
- `.actor/input_schema.json`: Apify input UI (fileupload plus JSON array, without nested item schemas).
- `tests/fixtures/alabama_roster.csv`: synthetic fixture shaped after fields displayed on the board's official detail page; values are fabricated for tests.
- `samples/sample-output.json`: one sample generated from that fixture, not from a live roster.
- `prospects.csv`: municipal office contacts from the public Alabama League of Municipalities Municipal Directory; entries are prospects only, and no one has been contacted.

The Actor folder can be deployed directly from this subfolder. Requirements are copied from [`ventures/apify-tools/requirements.txt`](../apify-tools/requirements.txt). No account signup, upload, publication, or payment has been performed.
