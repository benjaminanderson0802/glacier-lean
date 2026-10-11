#!/usr/bin/env python3
"""Create static HTML/SVG listing mockups and rasterize them with CairoSVG."""
from __future__ import annotations

from html import escape
from pathlib import Path
import cairosvg

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "screenshots"


def text(x: int, y: int, value: str, size: int = 18, fill: str = "#202632", weight: int = 400) -> str:
    return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill}">{escape(value)}</text>'


def rect(x: int, y: int, width: int, height: int, fill: str, radius: int = 0, stroke: str = "none") -> str:
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'


def browser_scene(hosted: bool) -> str:
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="800" viewBox="0 0 1280 800">',
             rect(0, 0, 1280, 800, "#e8edf3"), rect(0, 0, 1280, 42, "#dce3ec"),
             text(26, 27, "Chrome   ◂   ▸   ↻", 15, "#526174"), rect(155, 9, 820, 25, "#f8fafc", 12), text(176, 27, "https://shop.example/items/blendpro-8", 13, "#526174"),
             rect(0, 42, 1280, 44, "#ffffff"), text(28, 70, "shop  /  kitchen  /  blenders", 16, "#59687a"),
             rect(78, 132, 600, 526, "#ffffff", 12), rect(112, 162, 250, 244, "#edf2f7", 12),
             text(136, 218, "BLEND", 27, "#33465d", 700), text(136, 254, "PRO 8", 34, "#33465d", 700),
             rect(150, 322, 174, 8, "#d4dde7", 4), rect(150, 344, 142, 8, "#d4dde7", 4),
             text(398, 192, "BlendPro countertop blender", 25, "#202632", 700),
             text(398, 234, "Example Home", 16, "#64748b"), text(398, 288, "Model: BL-100", 17),
             text(398, 318, "UPC: 012345678905", 17), text(398, 372, "$89.00", 23, "#202632", 700),
             rect(398, 407, 174, 42, "#1e537c", 8), text(432, 434, "Add to cart", 16, "#ffffff", 700),
             text(112, 480, "A compact countertop blender for everyday use.", 16, "#4f5e70"),
             rect(1012, 42, 268, 758, "#ffffff", 0), rect(1012, 42, 268, 54, "#f7f9fc"),
             text(1032, 77, "Glacier Recall Checker", 15, "#202632", 700)]
    parts += [rect(1028, 110, 236, 664, "#f1f4f7", 14), text(1046, 143, "recall checker", 21, "#202632", 700),
              text(1046, 172, "Check the item in this tab. Page text stays", 11, "#4f5e70"), text(1046, 188, "in this browser; only the fields below are sent.", 11, "#4f5e70"),
              rect(1046, 205, 200, 31, "#ffffff", 7, "#b8c5d3"), text(1103, 226, "read this page", 13, "#1d2b3d", 700)]
    fields = [("barcode", "012345678905"), ("brand", "Example Home"), ("model", "BL-100"), ("product name", "BlendPro countertop blender")]
    y = 260
    for label, value in fields:
        parts.extend([text(1046, y, label, 11, "#344155"), rect(1046, y + 7, 200, 28, "#ffffff", 6, "#c8d2de"), text(1055, y + 26, value, 11, "#17202e")])
        y += 56
    parts.extend([text(1046, y + 1, "check with", 11, "#344155"), rect(1046, y + 8, 200, 28, "#ffffff", 6, "#c8d2de"), text(1055, y + 27, "hosted Apify Actor  ▾" if hosted else "this computer (default)  ▾", 11, "#17202e")])
    y += 47
    if hosted:
        parts.extend([rect(1046, y, 200, 70, "#ffffff", 6, "#c8d2de"), text(1055, y + 19, "hosted Actor settings", 11, "#344155", 700), text(1055, y + 39, "Actor ID    product-recall-checker", 9, "#526174"), text(1055, y + 57, "API token    •••••••••••••", 9, "#526174")])
        y += 81
    parts.extend([rect(1046, y, 200, 34, "#ffffff", 7, "#b8c5d3"), text(1116, y + 22, "check item", 13, "#1d2b3d", 700),
                  rect(1046, y + 46, 200, 90, "#e6f1e9", 8), text(1058, y + 69, "example match (illustrative)", 13, "#245333", 700),
                  text(1058, y + 90, "checked 2026-10-10", 10, "#526174"), text(1058, y + 114, "sample notice: 24001", 10, "#174f83"),
                  text(1046, 758, "Lookup aid. Confirm the official notice.", 10, "#4f5e70"), '</svg>'])
    return ''.join(parts)


def promo_scene() -> str:
    return ''.join(['<svg xmlns="http://www.w3.org/2000/svg" width="440" height="280" viewBox="0 0 440 280">', rect(0, 0, 440, 280, "#eaf0f6"),
        rect(14, 14, 412, 252, "#ffffff", 20, "#d5dee8"), rect(30, 30, 76, 76, "#1e537c", 18),
        text(49, 83, "RC", 32, "#ffffff", 700), text(124, 58, "glacier", 13, "#64748b"), text(124, 86, "recall checker", 25, "#202632", 700),
        text(31, 137, "Check the product you’re viewing", 19, "#334155", 700), text(31, 163, "against public recall records.", 19, "#334155", 700),
        rect(31, 186, 235, 42, "#1e537c", 10), text(48, 213, "read page • check item", 14, "#ffffff", 700),
        text(31, 249, "Your page stays in your browser.", 12, "#526174"), '</svg>'])


def icon_scene() -> str:
    return ''.join(['<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">',
        rect(0, 0, 128, 128, "#1e537c", 26), text(22, 82, "RC", 48, "#ffffff", 700), '</svg>'])


def write_mockup(filename: str, svg: str) -> None:
    (ROOT / "mockups").mkdir(exist_ok=True)
    html = '<!doctype html><meta charset="utf-8"><title>Recall checker listing mockup</title><body style="margin:0">' + svg + '</body>'
    (ROOT / "mockups" / filename).write_text(html, encoding="utf-8")
    png_name = filename.removesuffix(".html") + ".png"
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(OUT / png_name))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    write_mockup("01-local-check.html", browser_scene(False))
    write_mockup("02-hosted-mode.html", browser_scene(True))
    write_mockup("03-small-promo-tile.html", promo_scene())
    cairosvg.svg2png(bytestring=icon_scene().encode("utf-8"), write_to=str(ROOT / "store-icon-128.png"))
