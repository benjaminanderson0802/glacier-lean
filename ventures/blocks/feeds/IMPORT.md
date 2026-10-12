# Import an owner-downloaded feed snapshot

Use the offline importer when an official source is available in a normal browser or as an official download, while automated access is blocked. The importer reads only the file you point it at; it makes no HTTP requests and never reports a live fetch.

```python
from ventures.blocks.feeds.import_snapshot import import_snapshot

result = import_snapshot(
    "fsis_recalls",
    "/path/to/official-recall-export.json",
    source_url="https://www.fsis.usda.gov/news-events/news-feeds-subscriptions",
    acquired_at="2026-10-10",
    complete=True,  # confirm the downloaded file is a complete snapshot
)
print(result)
```

The source ID must already exist in `sources.json`. Supply the exact official page or download URL and the date the file was acquired in `YYYY-MM-DD` form. The URL must use HTTPS and the registered source host (with or without `www`); FDA's official `download.open.fda.gov` partition host is also accepted for FDA snapshots. Pass `complete=True` only after confirming the saved file is a complete snapshot; false is rejected. Inputs acquired more than 365 days ago are rejected by default. A caller may choose another limit from 0 through 3650 days. Future dates, empty or malformed files, HTML error/consent pages, unsupported source/format pairs, and files over 150 MB are rejected. CSV, TSV, and ZIP/XLSX expansion and parsed rows also have safety limits.

Supported saved formats follow the existing feed adapters: JSON for JSON record sources, CSV for OSHA ITA, HTML solicitation links for DIBBS, XLSX for CPSC documents, ZIP JSON partitions for openFDA, and ZIP/TSV for NHTSA. NHTSA's tabular ZIP requires the separately downloaded official RCL field dictionary via `dictionary_path`. HTML is parsed only for DIBBS; a DIBBS warning/consent page is refused. For JSON or archive downloads, wrapper totals are used when present. `expected_row_count` can supply an independently displayed count when the saved file has no total; any count difference above 1% is quarantined by the same policy used by network refresh.

The importer applies the feed's existing canary and schema checks before replacing a snapshot. Rejected candidates leave trusted rows and the remembered schema unchanged. Successful promotion records the source URL, acquisition date, SHA-256 of the imported bytes, parsed format, accepted row count, completeness assertion, and import timestamp in the local feed database. Row `fetched_at` values use the acquisition date. Reimporting identical bytes for that source returns `changed: false` and preserves the original provenance record.

All rows, provenance, and remembered schema are committed together in SQLite. A later successful network refresh replaces the offline snapshot and clears its import provenance, so offline metadata is never presented as provenance for a different snapshot.
