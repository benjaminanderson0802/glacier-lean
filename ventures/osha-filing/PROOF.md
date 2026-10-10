# OSHA filing preparation proof

- Focused acceptance suite: `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/osha-filing/tests` — **5 passed**.
- Bounded live public-source refresh: `GLACIER_HOME=/tmp/glacier-osha-x2 ~/w/glacier-lean/.venv/bin/python -m ventures.blocks.feeds.cli sync osha_ita` — **400,288 rows**, `changed: false`, **0 alerts**. The adapter fetched the current Summary Data CSV from OSHA's public ITA page (`https://www.osha.gov/itadata`) and normalized it without truncation. No customer injury data or filing was accessed/submitted.
