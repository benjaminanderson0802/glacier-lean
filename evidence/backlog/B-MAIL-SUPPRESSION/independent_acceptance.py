"""Independent acceptance cases for the public-records mail suppression list.

These fixtures are derived from ventures/SPEC.md (Public-records mail engine):
suppression applies, each do-not-mail request is honored before a later send,
and postcards are sent only through the approved test API path. They intentionally
exercise the public mail helpers without relying on a proposed implementation.

Run from the repository root:
  ./.venv/bin/python -m pytest -q evidence/backlog/B-MAIL-SUPPRESSION/independent_acceptance.py
"""
from __future__ import annotations

import importlib
from pathlib import Path
from unittest.mock import patch

import pytest

from ventures.blocks.mail import add_to_suppression, check_outreach
from ventures.blocks.mail import engine


SENDER = "Glacier Signs"
MESSAGE = "<p>Glacier Signs: information for your property.</p>"


def _check(address: object, path: Path) -> dict[str, str]:
    return check_outreach(
        {"sender": SENDER, "address": address}, MESSAGE, suppression_path=path
    )


@pytest.mark.parametrize(
    ("listed", "attempted"),
    [
        # Case-only changes in the same spelled address do not create a new recipient.
        (
            "42 Oak Street, Madison, WI 53703",
            "42 OAK STREET, MADISON, WI 53703",
        ),
        # Harmless spacing, punctuation, and documented field aliases are equivalent.
        (
            "42 Oak St., Apt. 2, Madison, WI 53703",
            {
                "line1": "  42 Oak Street  ",
                "line2": "Apartment 2",
                "city": "Madison",
                "state": "WI",
                "zip": "53703",
            },
        ),
    ],
    ids=["case-insensitive-spelling", "whitespace-punctuation-and-field-aliases"],
)
def test_equivalent_address_spelling_is_suppressed(
    tmp_path: Path, listed: object, attempted: object
) -> None:
    path = tmp_path / "do-not-mail.txt"
    add_to_suppression(listed, path=path)

    result = _check(attempted, path)

    assert result["verdict"] == "fail"
    assert "suppressed" in result["reason"].lower()


def test_zip_plus_four_and_five_digit_zip_represent_same_postal_address(
    tmp_path: Path,
) -> None:
    path = tmp_path / "do-not-mail.txt"
    add_to_suppression(
        {"line1": "42 Oak Street", "city": "Madison", "state": "WI", "zip": "53703"},
        path=path,
    )

    result = _check(
        {
            "address_line1": "42 Oak Street",
            "address_city": "Madison",
            "address_state": "WI",
            "address_zip": "53703-1234",
        },
        path,
    )

    assert result["verdict"] == "fail"
    assert "suppressed" in result["reason"].lower()


def test_suppression_keeps_distinct_apartment_identities(tmp_path: Path) -> None:
    path = tmp_path / "do-not-mail.txt"
    add_to_suppression(
        {
            "address_line1": "42 Oak Street",
            "address_line2": "Apt 2",
            "address_city": "Madison",
            "address_state": "WI",
            "address_zip": "53703",
        },
        path=path,
    )

    same_unit = _check(
        {
            "address_line1": "42 Oak Street",
            "address_line2": "Apt 2",
            "address_city": "Madison",
            "address_state": "WI",
            "address_zip": "53703",
        },
        path,
    )
    other_unit = _check(
        {
            "address_line1": "42 Oak Street",
            "address_line2": "Apt 3",
            "address_city": "Madison",
            "address_state": "WI",
            "address_zip": "53703",
        },
        path,
    )

    assert same_unit["verdict"] == "fail"
    assert other_unit["verdict"] == "pass"


def test_plain_text_suppression_survives_module_reload(tmp_path: Path) -> None:
    path = tmp_path / "do-not-mail.txt"
    add_to_suppression("10 Rue de l'Église, Québec", path=path)

    assert path.read_text(encoding="utf-8") == "10 rue de l'église, québec\n"
    importlib.reload(engine)
    result = _check("10 Rue de l'Église, Québec", path)

    assert result["verdict"] == "fail"
    assert "suppressed" in result["reason"].lower()


def test_new_request_is_applied_on_the_next_attempt(tmp_path: Path) -> None:
    path = tmp_path / "do-not-mail.txt"
    address = "42 Oak Street, Madison, WI 53703"

    assert _check(address, path)["verdict"] == "pass"
    add_to_suppression(address, path=path)
    second_attempt = _check(address, path)

    assert second_attempt["verdict"] == "fail"
    assert "suppressed" in second_attempt["reason"].lower()


def test_suppressed_postcard_never_requests_postal_api(tmp_path: Path) -> None:
    class NoRequestTransport:
        def __init__(self) -> None:
            self.calls: list[tuple[object, ...]] = []

        def request(self, *args: object, **kwargs: object) -> None:
            self.calls.append((*args, kwargs))
            raise AssertionError("suppressed postcard reached postal transport")

    transport = NoRequestTransport()
    address = {
        "address_line1": "42 Oak Street",
        "address_city": "Madison",
        "address_state": "WI",
        "address_zip": "53703",
    }
    suppression = tmp_path / "ventures" / "mail" / "do-not-mail.txt"
    add_to_suppression(address, path=suppression)

    with patch.dict("os.environ", {"GLACIER_HOME": str(tmp_path)}):
        with pytest.raises(ValueError, match="suppressed"):
            engine.postcard(
                "<p>Glacier Signs</p>",
                "<p>Information for your property.</p>",
                address,
                {"name": SENDER},
                approval_id="synthetic-approval",
                secret_getter=lambda _name: "test_synthetic_suppression",
                transport=transport,
            )

    assert transport.calls == []
