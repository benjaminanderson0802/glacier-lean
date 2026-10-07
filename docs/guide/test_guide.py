from pathlib import Path
import re


GUIDE = Path(__file__).parent
EXPECTED = [
    "README.md",
    "00-finding-your-way.md",
    "01-first-automation.md",
    "02-checks-and-trust.md",
    "03-memory.md",
    "04-safety-and-secrets.md",
    "05-when-something-breaks.md",
    "glossary.md",
]


def sentences(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"\[[^]]*\]\([^)]*\)", "link", text)
    text = re.sub(r"https?://\S+", "link", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.M)
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if re.search(r"[A-Za-z0-9]", s)]


def test_all_guide_files_exist():
    assert all((GUIDE / name).is_file() for name in EXPECTED)


def test_relative_links_resolve():
    for source in GUIDE.glob("*.md"):
        for target in re.findall(r"\[[^]]*\]\(([^)]+)\)", source.read_text()):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = target.split("#", 1)[0]
            assert path and (source.parent / path).exists(), f"{source.name}: {target}"


def test_lines_are_reasonably_short():
    for source in GUIDE.glob("*"):
        if source.suffix not in {".md", ".py"}:
            continue
        for number, line in enumerate(source.read_text().splitlines(), 1):
            assert len(line) <= 400, f"{source.name}:{number} is {len(line)} characters"


def test_average_sentence_length_is_at_most_20_words():
    for source in GUIDE.glob("*.md"):
        text = source.read_text()
        parts = sentences(text)
        average = sum(len(re.findall(r"\b[\w’'-]+\b", part)) for part in parts) / max(1, len(parts))
        assert average <= 20, f"{source.name}: average sentence length is {average:.1f} words"


def test_template_examples_use_real_template_names():
    text = (GUIDE / "01-first-automation.md").read_text()
    assert "**Daily report**" in text
    assert "**Explain an error**" in text
    assert "**Folder backup**" in text
    assert "**Website monitor**" in text
    assert "error explainer" not in text.lower()
    assert "website check" not in text.lower()


def test_secret_and_route_guidance_matches_main():
    text = (GUIDE / "04-safety-and-secrets.md").read_text()
    assert "AI step instructions can't use `{secret:...}`" in text
    assert "only be used in a command step" in text
    assert "hidden as `[secret name]` before it is saved or passed on" in text
    assert "the step fails" in text
    assert "one policy claim per day" in text
    assert "GLACIER_CODEX_SANDBOX" in text
    assert "Read-only means the AI can look at files but cannot change them" in text
    # Since PR #35 a step's own sandbox setting (including read-only) wins over GLACIER_CODEX_SANDBOX (runner.py).
    assert "A step's own setting, including read-only, takes precedence" in text
