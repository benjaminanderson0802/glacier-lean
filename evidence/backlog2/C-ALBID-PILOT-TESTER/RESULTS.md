# C-ALBID-PILOT-TESTER independent sample audit

## Drift check and scope

- **Checkpoint:** PH12.22 integration and independent audit; supports PH12.5 feed evidence. PH5 and PH9 remain in progress; this report does not claim either exit or PH12 completion.
- **Property/metrics:** P-VERIFY and P-USABLE; M-VERIFIED and M-INTERVENE.
- **Existing tools:** current local CSV parser, pytest and supplied source-linked fixture records; no service or dependency added.
- **Acceptance written first:** `ventures/al-bid-triage/tests/acceptance/test_C_al_bid_pilot.py` freezes expected fixture issuers, deadlines and URLs and expected uncertainty/conflict outcomes before invoking the unchanged generator.

## Results

- Independent check: `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/al-bid-triage/tests/acceptance/test_C_al_bid_pilot.py` — **5 passed**.
- Pilot test directory: `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/al-bid-triage/tests` — **30 passed, 1 skipped**. The skip is the opt-in public canary, run separately below.
- Public read-only listing canary: `RUN_LIVE=1 ~/w/glacier-lean/.venv/bin/python -m pytest -q -s ventures/al-bid-triage/tests/acceptance/test_al_bid_triage.py::test_live_official_document_contract` — **1 passed**, HTTP 200, `Alabama Builds` marker.

The two in-scope synthetic fixture rows retain their exact supplied issuer, deadline and URL in the generated digest. Missing issuer, deadline or pre-bid information yields `uncertain - please check`. A repeated notice ID with conflicting deadlines remains represented as a conflict, shows both supplied deadlines and yields the uncertainty phrase.

The fixture rows are customer/transcriber mappings, not official structured source records. Their `.example` URLs are synthetic. The canary only checked the public Alabama Builds listing page; it did not fetch or extract any notice. This audit establishes field preservation and uncertainty behavior for the supplied sample, not the accuracy or completeness of any real Alabama notice.

No triage code, existing tests, prospect files or outreach material were changed. Anti-pattern review: no existing check was edited or weakened; no checkpoint status was updated based on this report alone.
