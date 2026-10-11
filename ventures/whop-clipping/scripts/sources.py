"""Bounded, cached campaign source downloads with local provenance."""
from __future__ import annotations

import hashlib
import os
import shutil
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SourceResult:
    source_id: str
    path: Path
    url: str
    cached: bool
    provenance: dict


def _hash_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_direct(url: str, target: Path, max_bytes: int, timeout_s: int):
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": "WhopClipping/1.0"})
    with urllib.request.urlopen(request, timeout=min(timeout_s, 30)) as response, target.open("wb") as output:
        length = response.headers.get("Content-Length")
        if length and int(length) > max_bytes:
            raise ValueError(f"source exceeds configured size limit ({length} bytes)")
        total = 0
        while True:
            if time.monotonic() - started > timeout_s:
                raise TimeoutError("source download exceeded configured time limit")
            chunk = response.read(min(1024 * 1024, max_bytes - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("source exceeds configured size limit")
            output.write(chunk)


def fetch_source(url: str, source_id: str, *, cache_dir: Path, ledger=None,
                 max_bytes: int = 2_000_000_000, timeout_s: int = 1800) -> SourceResult:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "file":
        original = Path(urllib.request.url2pathname(parsed.path)).resolve()
        if not original.is_file():
            raise FileNotFoundError(original)
        if original.stat().st_size > max_bytes:
            raise ValueError("source exceeds configured size limit")
        suffix = original.suffix or ".media"
    elif parsed.scheme in {"http", "https"}:
        suffix = Path(parsed.path).suffix or ".media"
    else:
        raise ValueError("only http, https, and local file URLs are supported")
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    destination = cache_dir / f"{key}{suffix}"
    if destination.is_file() and destination.stat().st_size <= max_bytes:
        provenance = {"source_id": source_id, "url": url, "cached": True, "sha256": _hash_file(destination)}
        if ledger:
            ledger.record_source(source_id, url, destination, provenance["sha256"], provenance)
        return SourceResult(source_id, destination, url, True, provenance)

    started = time.monotonic()
    tmp = destination.with_suffix(destination.suffix + ".part")
    try:
        if parsed.scheme == "file":
            shutil.copyfile(original, tmp)
        else:
            host = (parsed.hostname or "").lower()
            if "youtube.com" in host or host.endswith("youtu.be"):
                try:
                    import yt_dlp
                except ImportError as exc:
                    raise RuntimeError("YouTube sources require the open-source yt-dlp package") from exc
                def enforce_time_limit(status):
                    if status.get("status") == "downloading" and time.monotonic() - started > timeout_s:
                        raise TimeoutError("source download exceeded configured time limit")

                options = {
                    "outtmpl": str(cache_dir / f"{key}.%(ext)s"), "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                    "merge_output_format": "mp4", "max_filesize": max_bytes, "socket_timeout": min(timeout_s, 30),
                    "noplaylist": True, "quiet": True, "no_warnings": True, "progress_hooks": [enforce_time_limit],
                }
                with yt_dlp.YoutubeDL(options) as downloader:
                    info = downloader.extract_info(url, download=True)
                downloaded = Path(downloader.prepare_filename(info))
                if not downloaded.exists():
                    downloaded = downloaded.with_suffix(".mp4")
                if not downloaded.exists():
                    raise RuntimeError("yt-dlp reported completion without a media file")
                if downloaded.stat().st_size > max_bytes:
                    downloaded.unlink(missing_ok=True)
                    raise ValueError("source exceeds configured size limit")
                if downloaded != destination:
                    shutil.move(str(downloaded), str(tmp))
                else:
                    tmp = destination
            elif "drive.google.com" in host:
                try:
                    import gdown
                except ImportError as exc:
                    raise RuntimeError("Google Drive sources require the open-source gdown package") from exc
                gdown.download(url, str(tmp), quiet=True, fuzzy=True)
            else:
                direct_url = url
                if host.endswith("dropbox.com"):
                    parts = urllib.parse.urlsplit(url)
                    query = urllib.parse.parse_qs(parts.query)
                    query["dl"] = ["1"]
                    direct_url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path,
                                                          urllib.parse.urlencode(query, doseq=True), parts.fragment))
                _download_direct(direct_url, tmp, max_bytes, min(timeout_s, 30))
        if time.monotonic() - started > timeout_s:
            raise TimeoutError("source download exceeded configured time limit")
        if not tmp.exists() or tmp.stat().st_size == 0:
            raise RuntimeError("source download returned no media")
        if tmp.stat().st_size > max_bytes:
            raise ValueError("source exceeds configured size limit")
        if tmp != destination:
            os.replace(tmp, destination)
    finally:
        tmp.unlink(missing_ok=True)
    digest = _hash_file(destination)
    provenance = {"source_id": source_id, "url": url, "cached": False, "sha256": digest,
                  "bytes": destination.stat().st_size, "downloaded_at": time.time()}
    if ledger:
        ledger.record_source(source_id, url, destination, digest, provenance)
    return SourceResult(source_id, destination, url, False, provenance)
