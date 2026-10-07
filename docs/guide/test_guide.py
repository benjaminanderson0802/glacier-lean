from pathlib import Path
import re


GUIDE = Path(__file__).parent
EXPECTED = [
    "README.md",
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
