#!/usr/bin/env python3
"""Independent, offline acceptance evaluator for B-MAIL-SECRETS.

Frozen from the card's mail security requirements and the pre-change mail
acceptance coverage. This evaluator deliberately knows nothing about engine
internals. It expects the public mail functions to accept two test seams:

    secret_getter(name: str) -> str | None
    transport.request(method, url, **kwargs) -> response

The transport response has ``status_code``, ``headers``, ``json()`` and
``text`` attributes. No actual keychain, credential, or network is used.
The synthetic secret is test-shaped and exists only in this process.

Run from the repository root with the project interpreter:
    .venv/bin/python evidence/backlog/B-MAIL-SECRETS/independent_acceptance.py

An implementation that does not expose these seams fails with a clear
interface assertion; the evaluator does not silently fall back to network or
environment credentials.
"""

from __future__ import annotations

import base64
import inspect
import os
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit
from unittest.mock import patch

# Running this file directly makes its evidence directory sys.path[0]. Add the
# repository root so the documented root-level invocation can import ventures.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ventures.blocks.mail import postcard, verify_address


TEST_SECRET = "test_independent_acceptance_synthetic_key"
ENV_SENTINEL = "environment_key_must_not_be_used"
SECRET_NAME = "LOB_API_KEY"
APPROVAL_ID = "approval-independent-acceptance"
APPROVED_ORIGIN = "https://api.lob.com"
APPROVED_PREFIX = "/v1/"


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload


class FakeTransport:
    """A deterministic request recorder; redirects are never auto-followed."""

    def __init__(self, response=None, error=None):
        self.calls = []
        self.response = response or FakeResponse(
            payload={"id": "lob_test_result", "deliverability": "deliverable",
                     "components": {"primary_line": "100 Main St"},
                     "expected_delivery_date": "2030-01-01"}
        )
        self.error = error

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.error is not None:
            raise self.error
        return self.response


class SecretGetter:
    def __init__(self, value):
        self.value = value
        self.lookups = []

    def __call__(self, name):
        self.lookups.append(name)
        return self.value if name == SECRET_NAME else None


def _assert_public_seams(testcase):
    """Fail explicitly instead of adapting to implementation internals."""
    for function in (postcard, verify_address):
        params = inspect.signature(function).parameters
        testcase.assertIn(
            "secret_getter", params,
            f"{function.__name__} must expose the injected Glacier Secrets getter seam",
        )
        testcase.assertIn(
            "transport", params,
            f"{function.__name__} must expose the injected mock HTTP transport seam",
        )


def _postcard(transport, getter, *, approval_id=None, output_dir=None):
    return postcard(
        "<main>Synthetic Sender — Front proof</main>",
        "<main>Synthetic Sender — Back proof</main>",
        {"name": "Synthetic Recipient", "address": "100 Main St", "city": "Madison",
         "state": "WI", "zip": "53703"},
        {"name": "Synthetic Sender", "address": "200 Lake St", "city": "Madison",
         "state": "WI", "zip": "53703"},
        approval_id=approval_id, output_dir=output_dir,
        secret_getter=getter, transport=transport,
    )


def _verify(transport, getter):
    return verify_address(
        {"address": "100 Main St", "city": "Madison", "state": "WI", "zip": "53703"},
        secret_getter=getter, transport=transport,
    )


def _contains_secret(value, secret):
    if isinstance(value, bytes):
        return secret.encode() in value
    if isinstance(value, str):
        return secret in value
    if isinstance(value, dict):
        return any(_contains_secret(k, secret) or _contains_secret(v, secret)
                   for k, v in value.items())
    if isinstance(value, (tuple, list, set)):
        return any(_contains_secret(item, secret) for item in value)
    return False


def _url_is_approved(url):
    return (url.startswith(APPROVED_ORIGIN + APPROVED_PREFIX)
            and "?" not in url.split("#", 1)[0]
            and "@" not in url[len("https://"):].split("/", 1)[0])


def _assert_authenticated_and_confined(testcase, calls):
    testcase.assertTrue(calls, "expected an authenticated Lob test request")
    for _method, url, kwargs in calls:
        testcase.assertTrue(_url_is_approved(url), f"unapproved authenticated URL: {url!r}")
        headers = {str(k).lower(): str(v) for k, v in kwargs.get("headers", {}).items()}
        auth = kwargs.get("auth")
        basic = base64.b64encode((TEST_SECRET + ":").encode()).decode()
        authorized = ("authorization" in headers and
                      (TEST_SECRET in headers["authorization"] or basic in headers["authorization"]))
        authorized = authorized or (isinstance(auth, (tuple, list)) and bool(auth)
                                    and auth[0] == TEST_SECRET)
        testcase.assertTrue(authorized, "request did not authenticate with the keychain test secret")
        testcase.assertFalse(_contains_secret(url, TEST_SECRET), "secret appeared in request URL")


class MailSecretsIndependentAcceptance(unittest.TestCase):
    def setUp(self):
        _assert_public_seams(self)

    def test_no_secret_renders_only_and_makes_no_http_request(self):
        transport = FakeTransport()
        getter = SecretGetter(None)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"LOB_API_KEY": ""}):
            result = _postcard(transport, getter, output_dir=tmp)
            self.assertEqual(result.get("status"), "render_only")
            for key in ("front_html", "back_html", "proof_pdf"):
                self.assertTrue(Path(result[key]).is_file(), f"missing render artifact: {key}")
            self.assertEqual(transport.calls, [], "render-only postcard attempted HTTP")
        self.assertIn(SECRET_NAME, getter.lookups, "Lob key was not resolved through Secrets")

    def test_glacier_secret_is_used_instead_of_environment_credential(self):
        transport = FakeTransport()
        getter = SecretGetter(TEST_SECRET)
        with patch.dict(os.environ, {"LOB_API_KEY": ENV_SENTINEL}):
            _verify(transport, getter)
        self.assertIn(SECRET_NAME, getter.lookups, "Lob credential was not requested from Secrets")
        _assert_authenticated_and_confined(self, transport.calls)
        self.assertFalse(_contains_secret(transport.calls, ENV_SENTINEL),
                         "environment credential was used instead of Glacier Secrets")

    def test_live_key_is_rejected_before_any_http_request(self):
        transport = FakeTransport()
        getter = SecretGetter("live_independent_acceptance_forbidden")
        with self.assertRaises(Exception):
            _postcard(transport, getter, approval_id=APPROVAL_ID)
        self.assertEqual(transport.calls, [], "live key reached the transport")

    def test_test_key_requires_explicit_approval(self):
        transport = FakeTransport()
        getter = SecretGetter(TEST_SECRET)
        with tempfile.TemporaryDirectory() as tmp:
            result = _postcard(transport, getter, output_dir=tmp)
        self.assertNotEqual(result.get("status"), "sent_test")
        self.assertEqual(transport.calls, [], "test-key request proceeded without explicit approval")

    def test_approved_test_key_request_is_authenticated_and_confined(self):
        transport = FakeTransport()
        getter = SecretGetter(TEST_SECRET)
        result = _postcard(transport, getter, approval_id=APPROVAL_ID)
        self.assertEqual(result.get("status"), "sent_test")
        self.assertEqual(result.get("approval_id"), APPROVAL_ID)
        _assert_authenticated_and_confined(self, transport.calls)
        self.assertEqual(
            [(method.upper(), urlsplit(url).path) for method, url, _kwargs in transport.calls],
            [("GET", "/v1/addresses/validate"), ("POST", "/v1/postcards")],
            "approved postcard must validate the address before submitting exactly one postcard",
        )

    def test_unapproved_host_or_path_is_rejected_before_transport(self):
        hostile_bases = (
            "https://evil.example/v1",
            "https://api.lob.com.evil.example/v1",
            "https://api.lob.com/v10",
            "http://api.lob.com/v1",
        )
        for base in hostile_bases:
            with self.subTest(base=base):
                transport = FakeTransport()
                getter = SecretGetter(TEST_SECRET)
                with patch.dict(os.environ, {"LOB_API_BASE_URL": base}):
                    with self.assertRaises(Exception, msg=f"accepted unapproved base {base}"):
                        _postcard(transport, getter, approval_id=APPROVAL_ID)
                self.assertEqual(transport.calls, [], f"transport called for unapproved base {base}")

    def test_off_host_redirect_is_rejected_without_following_or_leaking_auth(self):
        transport = FakeTransport(FakeResponse(
            status_code=302, headers={"Location": "https://evil.example/collect"},
            text="redirect",
        ))
        getter = SecretGetter(TEST_SECRET)
        with self.assertRaises(Exception):
            _postcard(transport, getter, approval_id=APPROVAL_ID)
        self.assertEqual(len(transport.calls), 1, "off-host redirect was followed")
        _assert_authenticated_and_confined(self, transport.calls)
        self.assertFalse(any("evil.example" in call[1] for call in transport.calls))

    def test_errors_do_not_disclose_secret(self):
        transport = FakeTransport(error=RuntimeError(f"synthetic upstream failure {TEST_SECRET}"))
        getter = SecretGetter(TEST_SECRET)
        try:
            _verify(transport, getter)
        except Exception as exc:
            public_error = str(exc)
        else:
            self.fail("transport error was unexpectedly accepted")
        self.assertNotIn(TEST_SECRET, public_error, "public error disclosed the Lob credential")


if __name__ == "__main__":
    unittest.main(verbosity=2)
