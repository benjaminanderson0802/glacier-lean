"""Generate an isolated fixed Codex corpus and measure session listing."""
from __future__ import annotations

import cProfile
import json
import os
import pstats
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[2] / "glacier" / "backend"))
CORPUS_FILES = 826
CORPUS_BYTES = 1_788_218_739
BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def line(value: dict) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"


def filler_line(index: int, width: int) -> bytes:
    stamp = (BASE_TIME + timedelta(seconds=2)).isoformat().replace("+00:00", "Z")
    payload = {"type": "agent_message", "message": "x" * width}
    return line({"type": "event_msg", "timestamp": stamp, "payload": payload})


def write_corpus(root: Path) -> tuple[int, int]:
    root.mkdir(parents=True)
    base, extra = divmod(CORPUS_BYTES, CORPUS_FILES)
    total = 0
    for index in range(CORPUS_FILES):
        target_size = base + (index < extra)
        stamp0 = BASE_TIME.isoformat().replace("+00:00", "Z")
        stamp1 = (BASE_TIME + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
        prefix = b"".join((
            line({"type": "session_meta", "payload": {"id": f"synthetic-{index:04d}", "cwd": "/synthetic/project", "timestamp": stamp0}}),
            line({"type": "event_msg", "timestamp": stamp1, "payload": {"type": "user_message", "message": f"Synthetic session title {index:04d}"}}),
        ))
        path = root / f"{index // 100:02d}" / f"{index:04d}.jsonl"
        path.parent.mkdir(exist_ok=True)
        with path.open("wb") as stream:
            stream.write(prefix)
            left = target_size - len(prefix)
            while left > 20_100:
                record = filler_line(index, 20_000)
                if len(record) > left:
                    break
                stream.write(record)
                left -= len(record)
            if left:
                # ASCII filler makes encoded line length linear, allowing exact sizing.
                empty = filler_line(index, 0)
                width = left - len(empty)
                if width < 0:
                    raise RuntimeError(f"Could not exactly fill synthetic file {index}: {left} bytes remain")
                final = filler_line(index, width)
                if len(final) != left:
                    raise RuntimeError(f"Synthetic file sizing mismatch {index}: {len(final)} != {left}")
                stream.write(final)
        total += target_size
    return CORPUS_FILES, total


def clear_reader_caches() -> None:
    import session_mirror
    from session_readers import opencode

    with session_mirror._CACHE_LOCK:
        session_mirror._FILE_CACHE.clear()
        session_mirror._EVENT_CACHE.clear()
    with opencode._CACHE_LOCK:
        opencode._FILE_CACHE.clear()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="glacier-synthetic-sessions-") as temporary:
        temp = Path(temporary)
        codex = temp / "codex"
        claude = temp / "claude"
        gemini = temp / "gemini"
        opencode = temp / "opencode"
        for folder in (claude, gemini, opencode):
            folder.mkdir()
        os.environ["GLACIER_CODEX_SESSIONS"] = str(codex)
        os.environ["GLACIER_CLAUDE_CODE_DATA"] = str(claude)
        os.environ["GLACIER_GEMINI_DATA"] = str(gemini)
        os.environ["GLACIER_OPENCODE_DATA"] = str(opencode)

        import session_mirror

        file_count, byte_count = write_corpus(codex)
        clear_reader_caches()
        start = time.perf_counter()
        cold_rows = session_mirror.list_sessions()
        cold_seconds = time.perf_counter() - start
        start = time.perf_counter()
        warm_rows = session_mirror.list_sessions()
        warm_seconds = time.perf_counter() - start

        expected = {f"synthetic-{index:04d}" for index in range(CORPUS_FILES)}
        assert len(cold_rows) == len(warm_rows) == CORPUS_FILES
        assert {row["id"] for row in cold_rows} == expected
        assert {row["id"] for row in warm_rows} == expected
        sample = cold_rows[0]
        assert sample["id"] == "synthetic-0000"
        assert sample["title"] == "Synthetic session title 0000"
        assert sample["started"] == "2026-01-01T00:00:00+00:00"
        assert sample["updated"] == "2026-01-01T00:00:02+00:00"
        assert all(row["title"].startswith("Synthetic session title ") for row in cold_rows)

        # Repeat the cache-cold scan under cProfile, matching the previous evidence method.
        clear_reader_caches()
        profiler = cProfile.Profile()
        prof_start = time.perf_counter()
        profiled_rows = profiler.runcall(session_mirror.list_sessions)
        profiled_seconds = time.perf_counter() - prof_start
        assert len(profiled_rows) == CORPUS_FILES
        profiler.dump_stats(str(ROOT / "synthetic-cold.prof"))
        with (ROOT / "synthetic-cold-profile.txt").open("w") as output:
            pstats.Stats(profiler, stream=output).strip_dirs().sort_stats("cumulative").print_stats(24)

        print(json.dumps({
            "corpus": "generated Codex JSONL only; other reader roots empty",
            "corpus_files": file_count,
            "corpus_bytes": byte_count,
            "returned_cold": len(cold_rows),
            "returned_warm": len(warm_rows),
            "cold_reader_cache_seconds": round(cold_seconds, 6),
            "warm_reader_cache_seconds": round(warm_seconds, 6),
            "profiled_reader_cache_cold_seconds": round(profiled_seconds, 6),
            "profiled_returned": len(profiled_rows),
            "sample_title": sample["title"],
            "sample_started": sample["started"],
            "sample_updated": sample["updated"],
            "timing_note": "Reader caches cleared; OS page cache not evicted.",
        }, indent=2))


if __name__ == "__main__":
    main()
