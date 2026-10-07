#!/usr/bin/env python3
"""Draw the app icon from the same pixel logo the screens use (glacier/web/src/ui/Pixel.tsx, mountains()).
Writes desktop/src-tauri/icons/icon.png (256 px) and icon.ico (16-256 px). Colours come from theme/tokens.css."""
import math
import re
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TOKENS = (ROOT / "glacier/web/src/theme/tokens.css").read_text(encoding="utf-8")


def token(name):
    value = re.search(rf"--g-{name}:\s*#([0-9a-fA-F]{{6}})", TOKENS).group(1)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def mountains():  # same algorithm as Pixel.tsx
    W, H = 26, 15
    peaks = [(9, 15), (18, 11)]
    rows = [["."] * W for _ in range(H)]
    for x in range(W):
        best, side = -1.0, 0
        for px, ph in peaks:
            hh = ph - abs(x - px) * 1.15
            if hh > best:
                best, side = hh, (0 if x <= px else 1)
        top = H - math.floor(best + 0.5)  # JavaScript Math.round
        for y in range(max(0, top), H):
            depth = y - top
            rows[y][x] = "w" if depth < 2 else ("w" if depth < 3 and (x + y) % 2 == 0 else ("a" if side == 0 else "l"))
    return ["".join(r) for r in rows]


def draw(size=256):
    rows = mountains()
    pal = {"w": token("head"), "a": token("accent"), "l": token("line")}
    grid = 32  # 26x15 logo centred on a 32x32 tile with the window background
    tile = Image.new("RGBA", (grid, grid), token("bg"))
    ox, oy = (grid - len(rows[0])) // 2, (grid - len(rows)) // 2 + 2
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c in pal:
                tile.putpixel((ox + x, oy + y), pal[c])
    return tile.resize((size, size), Image.NEAREST)


if __name__ == "__main__":
    out = ROOT / "desktop/src-tauri/icons"
    out.mkdir(parents=True, exist_ok=True)
    big = draw(256)
    big.save(out / "icon.png")
    big.save(out / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icons written to", out)
