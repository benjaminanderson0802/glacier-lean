# NPI Registry Batch Lookup and Normalizer

Look up exact NPI numbers in the official CMS NPPES registry. Normalize provider name, primary taxonomy, practice location, and source dates with explicit no-match and uncertainty.

## Input example

```json
{
  "npis": ["1881018208"]
}
```

Supply 1–50 ten-digit NPIs as strings. The Actor checks each check digit before making requests and queries duplicate values only once. It does not search by provider name.

## Output example

Selected fields from a recorded local SDK result on October 11, 2026 UTC. NPPES may update a record later; this sample is not a current credential or practice-status guarantee.

```json
{
  "record_id": "1881018208",
  "npi": "1881018208",
  "outcome": "ok",
  "billable": true,
  "message": "Public NPPES registry record only; not license, exclusion or credential verification.",
  "name": "MAYO CLINIC",
  "enumeration_type": "NPI-2",
  "registry_status": "A",
  "source_updated_at": "2021-04-12",
  "enumeration_date": "2014-02-05",
  "taxonomy_code": "261QM1300X",
  "taxonomy_description": "Clinic/Center, Multi-Specialty",
  "city": "ROCHESTER",
  "state": "MN",
  "postal_code": "559050001",
  "source_url": "https://npiregistry.cms.hhs.gov/api/?version=2.1&number=1881018208",
  "retrieved_at": "2026-10-11T03:03:41.402163+00:00"
}
```

Each returned NPI is one dataset row. The Actor selects the practice `LOCATION` address and a unique primary taxonomy when present. Missing optional values stay null with a warning. Source hashes, URLs, source dates, and retrieval times support checking the returned record.

## Result meaning and limits

`ok` means the exact NPI was returned by the registry. `no_match` means that query returned no public record; the message names NPPES and the retrieval date. It is free and is not proof that an NPI is invalid. `uncertain` means the response was unavailable, malformed, or did not match the requested identity; its message begins `uncertain - please check` and it is free. A valid check digit only verifies the number's format.

Uses the [CMS NPPES NPI Registry API](https://npiregistry.cms.hhs.gov/api-page). Registry presence is not licensure, credentialing, exclusion, Medicare participation, or permission to contact a provider. The Actor excludes phone/fax, authorized officials, and full source records. Never submit patient data. No accuracy rate or CMS endorsement is claimed; verify important facts with CMS.

## Pricing

The `provider-record` event costs **$0.003 per returned provider**, with platform usage included. No-match and uncertain results are free.

The maximum event charge per run is **$0.15** for 50 input NPIs. Fewer returned providers cost up to $0.003 each. Each new run can incur new event charges.
