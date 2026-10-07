from pathlib import Path
import re


PROPOSAL = Path(__file__).with_name("FUNDING_PROPOSAL.md")


def test_funding_proposal_has_required_sections_and_option_fees():
    text = PROPOSAL.read_text(encoding="utf-8")

    for heading in (
        "## Costs to cover",
        "## Funding options",
        "## Recommended first step",
        "## If the owner does nothing",
    ):
        assert heading in text

    for option in (
        "GitHub Sponsors",
        "Open Collective",
        "NLnet",
        "Sovereign Tech",
        "Paid support",
        "Donated CI capacity",
    ):
        start = text.index(option)
        next_option = min(
            (text.find(candidate, start + len(option)) for candidate in (
                "GitHub Sponsors", "Open Collective", "NLnet", "Sovereign Tech",
                "Paid support", "Donated CI capacity",
            ) if text.find(candidate, start + len(option)) != -1),
            default=len(text),
        )
        section = text[start:next_option]
        assert "fee" in section.lower(), f"{option} must name its fees"

    assert re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, re.I) is None
