# DIBBS intake provenance

`prepare_bids` creates a ranked row only when the supplied solicitation detail and supplier quote can be tied to the exact local source bytes and both records carry an owner confirmation for their current contents. This is an intake integrity check; it does not decide whether a bid is legally or commercially eligible.

## Required fields on each input record

Each solicitation detail and each supplier quote must include:

```json
{
  "source_provenance": {
    "path": "incoming/source-record.pdf",
    "sha256": "<lowercase SHA-256 of the exact local file bytes>",
    "acquired_at": "2026-10-10"
  },
  "superseded": false,
  "owner_confirmation": {
    "confirmed_by": "owner",
    "confirmed_at": "2026-10-10",
    "record_sha256": "<SHA-256 of this JSON record, excluding owner_confirmation>"
  }
}
```

Quote records must also include a non-empty `quote_revision`. `source_provenance.path` can be absolute. A relative path resolves under `$GLACIER_HOME/ventures/dibbs-supply/incoming/` (or `./ventures/dibbs-supply/incoming/` when `GLACIER_HOME` is unset). The declared source hash must match the file at intake time. Acquisition and confirmation dates use `YYYY-MM-DD`.

To compute `record_sha256`, serialize every record field except `owner_confirmation` with sorted keys, compact separators `(',', ':')`, and UTF-8 encoding, then calculate SHA-256. The record digest therefore binds the owner confirmation to the part, quantity, supplier, quote revision, source hash, acquisition date, and other supplied fields. Editing any of them requires a new confirmation digest. A record with `superseded` missing or true, or with a non-empty `superseded_by`, is withheld.

The file is not signed: `confirmed_by` records who the local operator says confirmed it, and the digest detects stale or mismatched confirmation data. It does not authenticate that person's identity or establish a legal approval.

## Output trace

Accepted ranked rows expose `input_provenance` for the solicitation and quote, including source path/hash, acquisition date, record digest, and confirmation details. The required DIBBS quote CSV keeps its solicitation-specific columns. `quote-provenance.json` maps each CSV data row to the solicitation and quote record/source digests, acquisition dates, and quote revision. The CSV remains unsigned; `submitted` remains false.

SAM.gov and DIBBS discovery remain discovery only. This intake reads the supplied local source artifacts and makes no DIBBS or supplier requests. The owner must provide current source files, acquisition dates, matching detail/quote records, quote revision, and fresh confirmations for real intake. SAM key setup, CAGE/registration, actual quotes, signature, and submission remain owner steps.
