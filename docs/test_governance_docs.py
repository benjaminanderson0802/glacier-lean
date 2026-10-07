"""Acceptance checks for the repository's contributor and release guidance."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DOCS = (
    "GOVERNANCE.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/ANNUAL_REVIEW.md",
)


def test_governance_documents_exist():
    for relative_path in DOCS:
        assert (ROOT / relative_path).is_file(), f"Missing {relative_path}"


def test_relative_markdown_links_resolve():
    link_pattern = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
    for relative_path in DOCS:
        document = ROOT / relative_path
        for raw_target in link_pattern.findall(document.read_text(encoding="utf-8")):
            target = raw_target.split("#", 1)[0].strip()
            if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            assert (document.parent / target).resolve().exists(), (
                f"Broken relative link in {relative_path}: {raw_target}"
            )


def test_governance_invariant_references_exist_in_northstar():
    northstar = (ROOT / "NORTHSTAR.yaml").read_text(encoding="utf-8")
    known_ids = set(re.findall(r"^\s*- I-(\d{2}):", northstar, re.MULTILINE))
    referenced_ids = set()
    for relative_path in DOCS:
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        referenced_ids.update(re.findall(r"\bI-(\d{2})\b", content))
    assert referenced_ids, "Governance docs should cite at least one invariant"
    assert referenced_ids <= known_ids, (
        f"Unknown North Star invariant references: {sorted(referenced_ids - known_ids)}"
    )
