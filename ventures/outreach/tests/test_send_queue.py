import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from send_queue import REQUIRED_COLUMNS, validate_csv


def write_csv(path, rows, columns=REQUIRED_COLUMNS):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows([{key: row.get(key, "") for key in columns} for row in rows])


def valid_row(**changes):
    row = {
        "venture": "sample",
        "business": "Example Supply",
        "contact_email": "office@example.com",
        "contact_form_url": "",
        "contact_source_url": "https://example.com/contact",
        "subject": "A short question about your catalog",
        "body": (
            "Your site lists industrial hose assemblies. I offer a $49 pilot. "
            "Details: https://example.com/pilot. Reply yes to get a free sample. "
            "Benjamin Anderson, Anderson Education LLC. "
            "{{POSTAL_ADDRESS}} Reply 'stop' and I won't email again."
        ),
        "followup_subject": "Following up about the sample",
        "followup_body": (
            "Following up once on the $49 pilot. Reply yes to get a free sample. "
            "{{POSTAL_ADDRESS}} Reply 'stop' and I won't email again."
        ),
    }
    row.update(changes)
    return row


def test_required_columns_are_checked(tmp_path):
    path = tmp_path / "batch.csv"
    write_csv(path, [valid_row()], columns=REQUIRED_COLUMNS[:-1])
    result = validate_csv(path)
    assert any("missing required columns" in error for error in result.errors)


def test_only_postal_address_placeholder_is_allowed(tmp_path):
    path = tmp_path / "batch.csv"
    row = valid_row(body=valid_row()["body"] + " Contact {{business}}.")
    write_csv(path, [row])
    result = validate_csv(path)
    assert any("placeholder" in error for error in result.errors)


def test_initial_and_followup_bodies_must_be_under_120_words(tmp_path):
    path = tmp_path / "batch.csv"
    long_body = "word " * 120
    write_csv(path, [valid_row(body=long_body)])
    result = validate_csv(path)
    assert any("120 words" in error for error in result.errors)


def test_business_is_deduplicated_across_queue(tmp_path):
    path = tmp_path / "batch.csv"
    write_csv(path, [valid_row(), valid_row(venture="another", contact_email="sales@example.com")])
    result = validate_csv(path)
    assert any("duplicate business" in error for error in result.errors)


def test_suppression_list_blocks_matching_email_and_business(tmp_path):
    path = tmp_path / "batch.csv"
    suppression = tmp_path / "suppression.csv"
    write_csv(path, [valid_row()])
    with suppression.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["contact_email", "business", "last_sent_at", "reason"])
        writer.writeheader()
        writer.writerow({"contact_email": "OFFICE@example.com", "business": ""})
    result = validate_csv(path, suppression)
    assert any("suppressed" in error for error in result.errors)


def test_recently_sent_business_is_suppressed_for_seven_days(tmp_path):
    from datetime import date, timedelta

    path = tmp_path / "batch.csv"
    suppression = tmp_path / "suppression.csv"
    write_csv(path, [valid_row(contact_email="new@example.com")])
    with suppression.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["contact_email", "business", "last_sent_at", "reason"])
        writer.writeheader()
        writer.writerow({
            "contact_email": "old@example.com",
            "business": "Example Supply",
            "last_sent_at": (date.today() - timedelta(days=3)).isoformat(),
            "reason": "sent",
        })
    result = validate_csv(path, suppression)
    assert any("contacted in the past 7 days" in error for error in result.errors)
