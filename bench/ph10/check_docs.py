"""Check guide Markdown links and the screen's help route targets."""
from __future__ import annotations

import re
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "guide"
SOURCE = ROOT / "glacier" / "web" / "src"


def main() -> int:
    failures: list[str] = []
    pages = sorted(GUIDE.glob("*.md"))
    for page in pages:
        body = page.read_text(encoding="utf-8")
        for target in re.findall(r"!?(?:\[[^\]]*\])\(([^)]+)\)", body):
            target = target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("https://", "http://", "mailto:", "#")):
                continue
            path = target.split("#", 1)[0].split("?", 1)[0]
            if path and not (page.parent / path).resolve().exists():
                failures.append(f"{page.relative_to(ROOT)}: missing {target}")

    settings = (SOURCE / "screens" / "Settings.tsx").read_text(encoding="utf-8")
    app = (SOURCE / "App.tsx").read_text(encoding="utf-8")
    palette = (SOURCE / "screens" / "CommandPalette.tsx").read_text(encoding="utf-8")
    route = SOURCE / "screens" / "Settings.tsx"
    for label, content in (("F1 help shortcut", app), ("Command palette help", palette)):
        if "settings/help" not in content:
            failures.append(f"{label}: settings/help route is missing")
    if "{ id: 'help'" not in settings or "cur.id === 'help'" not in settings:
        failures.append("Settings help section is not registered and rendered")
    if not route.is_file():
        failures.append("Settings screen file is missing")

    if failures:
        print("FAIL: guide/help links")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1
    print(f"PASS: {len(pages)} guide pages and screen help route")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
