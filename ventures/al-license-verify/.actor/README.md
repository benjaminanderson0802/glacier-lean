# Alabama Contractor Roster Verifier — Match License Numbers in Your CSV

Compare up to 100 license numbers or business names with a dated contractor roster CSV you are authorized to use. Receive structured matches, missing entries and uncertainty flags, with the roster date and source URL attached. This Actor reads your uploaded file; it does not query the Alabama board website.

## Use cases

- Check a subcontractor list against your organization's authorized roster snapshot.
- Find missing records before a person checks the board directly.
- Preserve the date and provenance of an internal roster comparison.

## Input example

Upload your authorized CSV through the **User-supplied roster CSV** input. Apify supplies the file reference. Replace the illustrative `YOUR_STORE_ID` reference below with that upload reference, and use the real roster date and source URL.

```json
{
  "roster_file": "https://api.apify.com/v2/key-value-stores/YOUR_STORE_ID/records/roster.csv",
  "roster_as_of": "2026-10-01",
  "source_url": "https://genconbd.alabama.gov/",
  "queries": [{"license_number": "AL-EXAMPLE-1042"}]
}
```

The license and date above are synthetic examples. The source URL is metadata, not proof that this file came from the board. Upload only a roster you may lawfully process on Apify.

CSV columns can include `License Number`, `Name`, `Status`, `Expiration Date` and `Specialty`. Each query has exactly one of `license_number` or `name`. Name matching is exact after case/punctuation normalization; it is not fuzzy identity matching. Maximum file size is 25 MiB; remote file references are restricted to HTTPS on `api.apify.com`, with no redirects.

## Output example

One dataset row from the repository's **synthetic fixture**, not a real contractor or a live board response:

```json
{
  "outcome": "match",
  "verification_state": "verified",
  "roster_presence": "listed",
  "license_number": "AL-EXAMPLE-1042",
  "business_name": "Example Building Services LLC",
  "status": "Active",
  "expiration_date": "2027-12-31",
  "specialty": "Building Construction",
  "source_url": "https://genconbd.alabama.gov/",
  "source_as_of": "2026-10-01",
  "checked_at": "2026-10-10T12:00:00+00:00",
  "limitations": "This snapshot only checks the supplied roster as of its stated date. It is not a real-time license determination, identity match, insurance check, or quality endorsement."
}
```

Export JSON or CSV from the default dataset. `verified` describes a readable comparison, not a current licensing determination. A listed inactive contractor still has `outcome: match`; read `status` separately. Old snapshots (over 365 days), ambiguous or incomplete data produce uncertainty. A missing entry means no match in the supplied roster as of its date.

## Pricing

Proposed launch price: **$0.01 per processed query**, event `license-lookup`, platform usage included; up to $1.00 for 100 billable comparisons. This is a recommendation pending owner configuration, not an active price. Read the Store pricing panel before running. Readable no-matches and results marked `uncertain` are charged; only `verification_state: unverifiable` avoids this event. Failed input/file loading does not produce a lookup event. No startup or automatic dataset-item charge is proposed.

## Limitations and legal notes

This is an uploaded-file comparison service, not a live Alabama license lookup. The owner has not established commercial redistribution permission for a board-wide roster. Do not upload, sell or redistribute board data without the necessary rights. Public listing remains gated on confirming an authorized data path. Source/date metadata is supplied by the user and is not independently authenticated.

No certification, identity confirmation, insurance verification, legal clearance or contractor endorsement is provided. Confirm important status questions with the [Alabama Licensing Board for General Contractors](https://genconbd.alabama.gov/). This Actor is independent of the board. Uploading a file sends it to Apify; exclude unnecessary personal data. Report technical problems in Apify Issues without attaching private rosters or credentials.
