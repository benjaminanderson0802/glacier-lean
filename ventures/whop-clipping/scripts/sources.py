"""Bounded, cached campaign source downloads with local provenance."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import zipfile
import http.cookiejar
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


def enforce_source_budget(cache_dir: Path, *, max_source_gb: float = 40, protected=()):
    """Remove least-recently-used cached files until the disk budget is met."""
    cache_dir = Path(cache_dir)
    protected = {Path(path).resolve() for path in protected}
    files = [path for path in cache_dir.rglob("*") if path.is_file() and not path.name.endswith(".part")]
    total = sum(path.stat().st_size for path in files)
    limit = max(0, int(float(max_source_gb) * 1024 ** 3))
    removed = []
    for path in sorted(files, key=lambda item: item.stat().st_atime):
        if total <= limit:
            break
        if path.resolve() in protected:
            continue
        size = path.stat().st_size
        path.unlink(missing_ok=True)
        total -= size
        removed.append(path)
    return removed


def _fetch_google_drive(url: str, target: Path, max_bytes: int, timeout_s: int):
    """Fetch a Drive file or folder via the open-source gdown package."""
    host_path = urllib.parse.urlparse(url).path.lower()
    if "/folders/" in host_path:
        folder = target.parent / f"{target.stem}.contents"
        folder.mkdir(parents=True, exist_ok=True)
        subprocess.run(["gdown", "--folder", url, "-O", str(folder)], check=True,
                       timeout=timeout_s, capture_output=True, text=True)
        media = [path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in
                 {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".mp3", ".wav", ".m4a"}]
        if not media:
            raise RuntimeError("Google Drive folder contains no supported media files")
        if sum(path.stat().st_size for path in folder.rglob("*") if path.is_file()) > max_bytes:
            raise ValueError("Google Drive folder exceeds configured size limit")
        media.sort(key=lambda path: path.stat().st_size, reverse=True)
        chosen = media[0]
        if chosen.stat().st_size > max_bytes:
            raise ValueError("source exceeds configured size limit")
        return chosen
    import gdown
    result = gdown.download(url, str(target), quiet=True, fuzzy=True)
    if not result:
        raise RuntimeError("gdown could not download the public Google Drive file")
    actual = Path(result)
    if actual.stat().st_size > max_bytes:
        raise ValueError("source exceeds configured size limit")
    return actual


def _fetch_dropbox(url: str, target: Path, max_bytes: int, timeout_s: int):
    """Download shared Dropbox files; shared folders arrive as ZIP archives."""
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qs(parsed.query)
    query["dl"] = ["1"]
    direct = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path,
                                      urllib.parse.urlencode(query, doseq=True), parsed.fragment))
    _download_direct(direct, target, max_bytes, timeout_s)
    if "/sh/" not in parsed.path and "/scl/fo/" not in parsed.path:
        return target
    folder = target.parent / f"{target.stem}.contents"
    folder.mkdir(parents=True, exist_ok=True)
    total = 0
    with zipfile.ZipFile(target) as archive:
        for item in archive.infolist():
            destination = (folder / item.filename).resolve()
            if folder.resolve() not in destination.parents and destination != folder.resolve():
                raise ValueError("Dropbox folder archive contains an unsafe path")
            if item.is_dir():
                continue
            total += item.file_size
            if total > max_bytes:
                raise ValueError("Dropbox folder exceeds configured size limit")
            archive.extract(item, folder)
    target.unlink(missing_ok=True)
    media = [path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in
             {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".mp3", ".wav", ".m4a"}]
    if not media:
        raise RuntimeError("Dropbox folder contains no supported media files")
    media.sort(key=lambda path: path.stat().st_size, reverse=True)
    return media[0]


def _fetch_wetransfer(url: str, target: Path, max_bytes: int, timeout_s: int):
    """Resolve a public WeTransfer URL and fetch its signed download link."""
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WhopClipping/1.0"
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with opener.open(request, timeout=min(timeout_s, 30)) as response:
        final_url = response.geturl()
    parts = [part for part in urllib.parse.urlsplit(final_url).path.split("/") if part]
    if parts and parts[0] == "downloads":
        parts = parts[1:]
    if len(parts) == 2:
        transfer_id, security_hash = parts
        recipient_id = None
    elif len(parts) == 3:
        transfer_id, recipient_id, security_hash = parts
    else:
        raise ValueError("unrecognized public WeTransfer link; expected transfer and security hash")
    body = {"intent": "entire_transfer", "security_hash": security_hash}
    if recipient_id:
        body["recipient_id"] = recipient_id
    home_request = urllib.request.Request("https://wetransfer.com/", headers={"User-Agent": user_agent})
    with opener.open(home_request, timeout=min(timeout_s, 30)) as response:
        landing_page = response.read().decode("utf-8", errors="replace")
    csrf = re.search(r'name="csrf-token"\s+content="([^"]+)"', landing_page)
    headers = {"User-Agent": user_agent, "Content-Type": "application/json",
               "X-Requested-With": "XMLHttpRequest", "Origin": "https://wetransfer.com"}
    if csrf:
        headers["X-CSRF-Token"] = csrf.group(1)
    api_request = urllib.request.Request(
        f"https://wetransfer.com/api/v4/transfers/{transfer_id}/download",
        data=json.dumps(body).encode("utf-8"), method="POST",
        headers=headers)
    with opener.open(api_request, timeout=min(timeout_s, 30)) as response:
        metadata = json.loads(response.read().decode("utf-8"))
    direct_url = metadata.get("direct_link")
    if not direct_url:
        raise RuntimeError("WeTransfer did not provide a public download link")
    _download_direct(direct_url, target, max_bytes, timeout_s)
    expiry = next((metadata[key] for key in ("expires_at", "expiry", "expiration_date") if metadata.get(key)), None)
    if expiry is None and isinstance(metadata.get("transfer"), dict):
        transfer = metadata["transfer"]
        expiry = next((transfer[key] for key in ("expires_at", "expiry", "expiration_date")
                       if transfer.get(key)), None)
    return {"download_url": direct_url, "expires_at": expiry or "unknown", "transfer_id": transfer_id}


def fetch_source(url: str, source_id: str, *, cache_dir: Path, ledger=None,
                 max_bytes: int = 2_000_000_000, timeout_s: int = 1800, max_source_gb: float = 40) -> SourceResult:
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
    metadata_path = cache_dir / f"{key}.source.json"
    if destination.is_file() and destination.stat().st_size <= max_bytes:
        os.utime(destination, None)
        try:
            cached_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached_metadata = {}
        provenance = {**cached_metadata, "source_id": source_id, "url": url, "cached": True,
                      "sha256": _hash_file(destination)}
        if ledger:
            ledger.record_source(source_id, url, destination, provenance["sha256"], provenance)
        return SourceResult(source_id, destination, url, True, provenance)

    started = time.monotonic()
    tmp = destination.with_suffix(destination.suffix + ".part")
    extra_provenance = {}
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
                actual = _fetch_google_drive(url, tmp, max_bytes, timeout_s)
                if actual != tmp:
                    shutil.move(str(actual), str(tmp))
            elif host.endswith("wetransfer.com") or host.endswith("we.tl"):
                extra_provenance = _fetch_wetransfer(url, tmp, max_bytes, timeout_s)
            elif host.endswith("dropbox.com"):
                actual = _fetch_dropbox(url, tmp, max_bytes, timeout_s)
                if actual != tmp:
                    shutil.move(str(actual), str(tmp))
            else:
                _download_direct(url, tmp, max_bytes, min(timeout_s, 30))
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
                  "bytes": destination.stat().st_size, "downloaded_at": time.time(), **extra_provenance}
    metadata_path.write_text(json.dumps(provenance, sort_keys=True), encoding="utf-8")
    enforce_source_budget(cache_dir, max_source_gb=max_source_gb, protected={destination})
    if ledger:
        ledger.record_source(source_id, url, destination, digest, provenance)
    return SourceResult(source_id, destination, url, False, provenance)
