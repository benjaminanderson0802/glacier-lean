"""Acceptance checks for the static pilot-offer site."""

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


SITE = Path(__file__).resolve().parents[1]
PAGES = (
    "index.html",
    "job-closeout.html",
    "sam-amendment-alerts.html",
    "al-bid-triage.html",
    "al-license-verify.html",
    "fba-fee-check.html",
    "privacy.html",
    "contact.html",
)
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])


class StaticSiteAcceptance(unittest.TestCase):
    def test_required_pages_exist_and_local_links_resolve(self):
        for page in PAGES:
            path = SITE / page
            self.assertTrue(path.is_file(), f"missing required page: {page}")
            parser = LinkParser()
            parser.feed(path.read_text(encoding="utf-8"))
            for href in parser.links:
                if href.startswith(("https://", "http://", "mailto:", "#")):
                    continue
                target = (path.parent / href.split("#", 1)[0]).resolve()
                self.assertTrue(target.is_relative_to(SITE.resolve()), f"link escapes site: {page} -> {href}")
                self.assertTrue(target.exists(), f"broken local link: {page} -> {href}")

    def test_email_placeholder_and_no_phone_contact(self):
        for path in SITE.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts or "tests" in path.parts:
                continue
            content = path.read_bytes()
            text = content.decode("utf-8", errors="ignore")
            self.assertNotRegex(text, PHONE_PATTERN, f"phone-style number in {path.relative_to(SITE)}")
            self.assertNotRegex(text.lower(), r"(?:href\s*=\s*[\"']tel:|\bphone\b|\bcall us\b)", f"phone contact in {path.relative_to(SITE)}")

        contact = (SITE / "contact.html").read_text(encoding="utf-8")
        self.assertIn("{{BUSINESS_EMAIL}}", contact)
        self.assertNotIn("mailto:{{BUSINESS_EMAIL}}", contact, "placeholder must not be presented as a usable address")


if __name__ == "__main__":
    unittest.main()
