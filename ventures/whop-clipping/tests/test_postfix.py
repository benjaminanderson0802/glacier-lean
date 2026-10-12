from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

VENTURE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VENTURE_DIR))

from scripts.distributor import _channel_variant
from scripts.interfaces import Campaign, Clip
from scripts.producer import parse_campaign_requirements, qa_clip
from scripts.variants import STYLES, make_variant, normalize_caption_words


RULES = """Required in every YouTube Shorts post: tag @boxabl in the caption/description; the caption must mention Boxabl and be relevant (Casita, foldable homes, factory, product).
On-video captions: must spell BOXABL correctly; show the whole home, with a clear BOXABL mention (spoken or on-screen) when the home is shown.
Banned: clips of Kanye; mentioning Boxabl stock or any ticker; story boosting; negativity/mocking; low-effort bait."""


def _campaign(**changes):
    row = Campaign("box", "Boxabl Official Clipping", "https://contentrewards.com/c/campaigns/secret",
                   1.0, None, ["youtube_shorts"], RULES)
    for key, value in changes.items():
        setattr(row, key, value)
    return row


def _clip(path, *, text="The Box Able Casita folds into a complete home.", title="Boxabl Casita #shorts"):
    return Clip("clip", "box", "source", 0, 30, str(path), title,
                "@boxabl #shorts\n\n" + text, ["#shorts"], "@alpha",
                caption_words=[{"start": 0, "end": 0.5, "word": token}
                               for token in text.split()])


@pytest.mark.parametrize("channel", ["@frameandmomentdesk", "@highlightdesknotes", "@quickreplaydesk"])
def test_required_handles_and_hashtags_are_first_description_line_and_title_when_fitting(channel):
    variant = make_variant(_campaign(), {"text": "So this is the Casita, it folds.", "words": []}, channel)
    first_line = variant["description"].splitlines()[0]
    assert "@boxabl" in first_line
    assert "#shorts" in first_line
    assert "@boxabl" in variant["title"]
    assert "#shorts" in variant["title"]


def test_public_metadata_omits_rules_internal_campaign_name_and_campaign_url():
    variant = make_variant(_campaign(), {"text": "The Casita folds into a home.", "words": []}, "@alpha")
    public = variant["title"] + "\n" + variant["description"]
    assert "Boxabl Official Clipping" not in public
    assert "Clipping" not in public
    assert "contentrewards.com" not in public
    assert "Campaign:" not in public
    assert "rules" not in public.lower()


def test_qa_rejects_legacy_metadata_that_leaks_campaign_name_url_or_rules(tmp_path):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"clip")
    clip = _clip(path)
    clip.title = "Boxabl Official Clipping - BOXABL #shorts"
    clip.description = ("@boxabl #shorts\n\nBOXABL: A Casita folds.\n"
                        "Campaign: Boxabl Official Clipping\n"
                        "https://contentrewards.com/c/campaigns/secret\n"
                        "mention Boxabl and be relevant (Casita, foldable homes, factory, product)")
    checklist = {**parse_campaign_requirements(RULES), "campaign_name": "Boxabl Official Clipping",
                 "campaign_url": "https://contentrewards.com/c/campaigns/secret"}
    failures = qa_clip(clip, checklist, word_times=clip.caption_words)
    assert any("internal campaign name" in failure for failure in failures)
    assert any("internal campaign URL" in failure for failure in failures)
    assert any("campaign rule text" in failure for failure in failures)


def test_title_mentions_brand_is_short_clean_and_has_shorts_tag():
    title = make_variant(_campaign(), {"text": "So this is the Boxabl Casita, it folds", "words": []}, "@alpha")["title"]
    assert "BOXABL" in title
    assert len(title) <= 100
    assert title.endswith("#shorts")
    assert "it folds" not in title.lower()
    assert not title.endswith(("it folds", "it", "folds"))


@pytest.mark.parametrize("transcript,matched", [
    ("Kanye walks onto the stage.", "Kanye"),
    ("The speaker discusses Boxabl stock today.", "stock"),
])
def test_banned_transcript_topics_fail_qa_and_quote_the_rule(tmp_path, transcript, matched):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"clip")
    clip = _clip(path, text=transcript)
    failures = qa_clip(clip, parse_campaign_requirements(RULES), word_times=clip.caption_words)
    assert any("Banned:" in failure and matched in failure for failure in failures)


def test_any_ticker_is_banned_but_the_brand_name_is_not_a_ticker(tmp_path):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"clip")
    valid = _clip(path, text="BOXABL Casita fits into a complete home.")
    assert not any("banned campaign rule" in failure
                   for failure in qa_clip(valid, parse_campaign_requirements(RULES),
                                          word_times=valid.caption_words))
    ticker = _clip(path, text="The TSLA ticker gained value.")
    failures = qa_clip(ticker, parse_campaign_requirements(RULES), word_times=ticker.caption_words)
    assert any("Banned:" in failure and "TSLA" in failure for failure in failures)


def test_caption_and_title_spelling_maps_whisper_mishearing_to_exact_brand_case(tmp_path, monkeypatch):
    variant = make_variant(_campaign(), {"text": "Box able has a folding home.", "words": []}, "@alpha")
    assert "BOXABL" in variant["title"]
    assert "@boxabl" in variant["title"]
    assert "@BOXABL" not in variant["title"]
    clip = _clip(tmp_path / "base.mp4")
    clip.path = str(tmp_path / "base.mp4")
    clip.end_s = 2
    captured = {}

    def fake_render(_source, target, **kwargs):
        captured.update(kwargs)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"rendered")

    monkeypatch.setattr("scripts.clipper.render_clip", fake_render)
    variant = _channel_variant(clip, _campaign(), {}, tmp_path, {})
    assert any(word["word"] == "BOXABL" for word in variant.caption_words)
    assert any(word["word"] == "BOXABL" for word in captured["caption_words"])


def test_generated_spelling_compliance_passes_qa_without_upcasing_required_handle(tmp_path):
    campaign = _campaign()
    result = make_variant(campaign, {"text": "The Box able Casita folds into place."}, "@alpha")
    words = normalize_caption_words([
        {"start": 0, "end": 0.2, "word": "The"},
        {"start": 0.2, "end": 0.3, "word": "Box"},
        {"start": 0.3, "end": 0.5, "word": "able"},
        {"start": 0.5, "end": 0.8, "word": "Casita"},
    ], campaign.rules_text, "Boxabl")
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"clip")
    clip = Clip("clip", campaign.id, "source", 0, 30, str(path), result["title"],
                result["description"], result["hashtags"], "@alpha", caption_words=words)
    checklist = {**parse_campaign_requirements(campaign.rules_text),
                 "campaign_name": campaign.name, "campaign_url": campaign.url,
                 "required_brand": "Boxabl"}
    assert not qa_clip(clip, checklist, word_times=words)


@pytest.mark.parametrize("style_index", range(len(STYLES)))
def test_distributor_burns_colored_word_captions_for_each_style(style_index, tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg is required for rendered caption verification")
    from scripts.variants import CHANNEL_STYLE_INDEX

    channel = next(key for key, index in CHANNEL_STYLE_INDEX.items() if index == style_index)
    source = tmp_path / "speech.mp4"
    subprocess.run([ffmpeg, "-v", "error", "-f", "lavfi", "-i", "color=c=navy:s=320x240:d=2",
                    "-i", str(VENTURE_DIR / "tests/fixtures/short-speech.wav"), "-shortest", "-y", str(source)],
                   check=True)
    words = [{"start": 0.2, "end": 0.8, "word": "BOXABL"},
             {"start": 0.9, "end": 1.5, "word": "Casita"}]
    clip = Clip(f"clip-{style_index}", "box", "source", 0, 2, str(source), "BOXABL Casita #shorts",
                "@boxabl #shorts\n\nBOXABL: BOXABL Casita", ["#shorts"], channel,
                caption_words=words)
    campaign = _campaign(rules_text="Spell BOXABL in all captions.")
    variant = _channel_variant(clip, campaign, {}, tmp_path, {})
    rendered_path = Path(variant.path)
    ass = rendered_path.with_suffix(".ass")
    assert ass.is_file() and "BOXABL" in ass.read_text(encoding="utf-8")
    from scripts.clipper import render_clip
    base_path = tmp_path / "base-render.mp4"
    render_clip(source, base_path, start_s=0, end_s=2, caption_words=[])
    base_frame = tmp_path / "base.png"
    rendered_frame = tmp_path / "rendered.png"
    subprocess.run([ffmpeg, "-v", "error", "-ss", "0.5", "-i", str(base_path), "-frames:v", "1", "-y", str(base_frame)], check=True)
    subprocess.run([ffmpeg, "-v", "error", "-ss", "0.5", "-i", str(rendered_path), "-frames:v", "1", "-y", str(rendered_frame)], check=True)
    assert base_frame.read_bytes() != rendered_frame.read_bytes()
