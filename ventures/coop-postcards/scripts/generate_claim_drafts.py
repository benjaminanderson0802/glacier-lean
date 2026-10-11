"""Read completed Jobber jobs and write local co-op claim drafts only."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ventures.blocks.connectors import JobberClient
from workflow import generate_claim_draft


def _load_fixture(path: Path) -> tuple[str, list[dict], dict[str, dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return str(payload["dealer_label"]), payload["jobs"], payload.get("details_by_job_id", {})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, help="local Jobber-shaped fixture (offline proof only)")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    home = Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier"))
    output_dir = args.output_dir or home / "ventures/coop-postcards/claims"
    try:
        if args.fixture:
            dealer, jobs, details_by_id = _load_fixture(args.fixture)
            source = "fixture"
        else:
            client = JobberClient()
            try:
                account = client.test_connection()
                dealer = str(account.get("account") or "Jobber dealer")
                jobs = client.get_jobs(max_pages=5)
            finally:
                client.close()
            jobs = [job for job in jobs if str(job.get("jobStatus", "")).casefold() in {"completed", "complete"}]
            detail_dir = home / "ventures/coop-postcards/job-details"
            details_by_id = {}
            if detail_dir.is_dir():
                details_by_id = {item.stem: json.loads(item.read_text(encoding="utf-8")) for item in detail_dir.glob("*.json")}
            source = "Jobber read-only connector"
        drafts = []
        for job in jobs:
            if str(job.get("jobStatus", "")).casefold() not in {"completed", "complete"}:
                continue
            job_id = str(job.get("id") or job.get("jobNumber") or "")
            details = details_by_id.get(job_id, {})
            draft = generate_claim_draft(job, dealer, details=details, output_dir=output_dir)
            draft["intake_source"] = source
            Path(draft["record_path"]).write_text(json.dumps(draft, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            drafts.append({key: draft[key] for key in ("claim_id", "job_number", "brand", "rule_status", "markdown_path", "pdf_path", "deadline_status", "filing_ready", "external_action")})
        from ventures.blocks.deadlines import due as due_deadlines
        reminders = due_deadlines(date.today())
        print(json.dumps({"dealer": dealer, "source": source, "drafts_created": len(drafts), "drafts": drafts,
                          "deadline_reminders_due": reminders, "external_actions": "none"}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        print(json.dumps({"status": "uncertain", "error": str(exc), "external_actions": "none"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
