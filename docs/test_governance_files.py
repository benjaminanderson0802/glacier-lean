"""Acceptance checks for the PH11.2 governance files."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_governance_files_exist():
    expected = (
        "SECURITY.md",
        "GOVERNANCE.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        ".github/ISSUE_TEMPLATE/bug.md",
        ".github/ISSUE_TEMPLATE/feature.md",
        ".github/ISSUE_TEMPLATE/config.yml",
        ".github/pull_request_template.md",
    )
    for relative_path in expected:
        assert (ROOT / relative_path).is_file(), f"Missing {relative_path}"


def test_security_policy_uses_private_github_reporting_without_email():
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert not re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", security, re.I)
    assert re.search(r"private vulnerability reporting", security, re.I)
    assert re.search(r"\*\*Security tab\*\*\s*>\s*\*\*Report a vulnerability\*\*", security, re.I)


def test_contributing_names_theme_tokens_and_lint():
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "glacier/web/src/theme/tokens.css" in contributing
    assert re.search(r"theme lint", contributing, re.I)
