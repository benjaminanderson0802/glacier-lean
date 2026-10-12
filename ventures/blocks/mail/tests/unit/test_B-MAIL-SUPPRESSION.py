from pathlib import Path

import pytest

from ventures.blocks.mail import engine
from ventures.blocks.mail.engine import add_to_suppression, check_outreach


SENDER = "Glacier Signs"
MESSAGE = "<p>Glacier Signs: information for your property.</p>"


def _check(address: object, path: Path) -> dict[str, str]:
    return check_outreach(
        {"sender": SENDER, "address": address}, MESSAGE, suppression_path=path
    )


def test_equivalent_punctuation_alias_whitespace_and_zip_are_suppressed(tmp_path: Path) -> None:
    path = tmp_path / "do-not-mail.txt"
    add_to_suppression("42 Oak St., Apt. 2, Madison, WI 53703-1234", path=path)

    result = _check(
        {
            "line1": "  42 OAK STREET  ",
            "line2": "Apartment 2",
            "city": "Madison",
            "state": "WI",
            "zip": "53703",
        },
        path,
    )

    assert result["verdict"] == "fail"
    assert "suppressed" in result["reason"].lower()


def test_suppression_does_not_cross_unit_identity(tmp_path: Path) -> None:
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

    result = _check(
        {
            "address_line1": "42 Oak St",
            "address_line2": "Suite 3",
            "address_city": "Madison",
            "address_state": "WI",
            "address_zip": "53703-1234",
        },
        path,
    )

    assert result["verdict"] == "pass"


def test_normalized_suppression_remains_plain_text_and_durable(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "do-not-mail.txt"
    address = "10 Rue de l'Église, Québec"
    add_to_suppression(address, path=path)
    add_to_suppression(address.upper(), path=path)

    assert path.read_text(encoding="utf-8") == "10 rue de l'église, québec\n"
    assert _check(address, path)["verdict"] == "fail"


def test_postcard_rechecks_suppression_after_address_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    suppression = tmp_path / "ventures" / "mail" / "do-not-mail.txt"
    address = {
        "address_line1": "42 Oak Street",
        "address_city": "Madison",
        "address_state": "WI",
        "address_zip": "53703",
    }

    class Response:
        status_code = 200

        @staticmethod
        def json() -> dict[str, str]:
            return {"deliverability": "deliverable"}

    class OptOutDuringVerification:
        def __init__(self) -> None:
            self.paths: list[str] = []

        def request(self, method: str, url: str, **_kwargs: object) -> Response:
            self.paths.append(url)
            add_to_suppression(address, path=suppression)
            return Response()

    transport = OptOutDuringVerification()
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    monkeypatch.setattr(engine, "_proof_pdf", lambda *_args, **_kwargs: None)

    with pytest.raises(ValueError, match="suppressed"):
        engine.postcard(
            "<p>Glacier Signs</p>",
            "<p>Information for your property.</p>",
            address,
            {"name": SENDER},
            approval_id="synthetic-approval",
            output_dir=tmp_path / "proof",
            secret_getter=lambda _name: "test_synthetic_suppression",
            transport=transport,
        )

    assert len(transport.paths) == 1
    assert transport.paths[0].endswith("/addresses/validate")
