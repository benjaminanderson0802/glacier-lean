#!/usr/bin/env python3
"""Prove that API-visible Memory survives deleting and restoring GLACIER_HOME.

Runs the real backend twice. The only restore input is a local bare Git remote;
the rebuilt SQLite index is disposable and is repopulated from the cloned notes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "glacier" / "backend"
TOKEN = "memory-reinstall-proof-token"
FAKE_CODEX = BACKEND / "tests" / "fake_codex.py"


class ProofFailure(RuntimeError):
    pass


class Backend:
    def __init__(self, home: Path):
        self.home = home
        self.port = self._free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.process: subprocess.Popen | None = None
        self.log = None

    @staticmethod
    def _free_port() -> int:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    def start(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        self.log = (self.home / "proof-backend.log").open("ab")
        env = dict(os.environ)
        env.update(GLACIER_HOME=str(self.home), GLACIER_TOKEN=TOKEN, CODEX_BIN=str(FAKE_CODEX), GLACIER_AUTO_RESEARCH="0")
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(self.port)],
            cwd=BACKEND,
            env=env,
            stdout=self.log,
            stderr=subprocess.STDOUT,
            start_new_session=(os.name != "nt"),
        )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise ProofFailure(f"Backend exited during startup; see {self.home / 'proof-backend.log'}")
            try:
                self.request("GET", "/api/environments")
                return
            except (OSError, urllib.error.URLError, ProofFailure):
                time.sleep(0.1)
        raise ProofFailure(f"Backend did not start; see {self.home / 'proof-backend.log'}")

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            if os.name == "nt":
                self.process.terminate()
            else:
                os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    self.process.kill()
                else:
                    os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
        if self.log:
            self.log.close()

    def request(self, method: str, path: str, payload: dict | None = None):
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            self.base + path,
            data=body,
            method=method,
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise ProofFailure(f"{method} {path} returned HTTP {exc.code}: {exc.read().decode(errors='replace')}") from exc
        return json.loads(raw) if raw else None


def timed(rows: list[tuple[str, str, float]], label: str, action):
    started = time.monotonic()
    try:
        action()
    except Exception as exc:
        rows.append((label, "FAIL", time.monotonic() - started))
        raise ProofFailure(f"{label}: {exc}") from exc
    rows.append((label, "PASS", time.monotonic() - started))


def note_snapshot(server: Backend) -> dict:
    notes = server.request("GET", "/api/memory/notes")
    paths = sorted(item["path"] for item in notes)
    details = {}
    for path in paths:
        encoded = urllib.parse.quote(path, safe="")
        item = server.request("GET", f"/api/memory/note?path={encoded}")
        details[path] = {
            "body": item["body"],
            "links_in": sorted(item["links_in"]),
            "links_out": sorted(item["links_out"]),
        }
    graph = server.request("GET", "/api/memory/graph")
    graph_snapshot = {
        "nodes": sorted((n["id"], n["title"], n["kind"], n["author"]) for n in graph["nodes"]),
        "edges": sorted((e["source"], e["target"], e["kind"]) for e in graph["edges"]),
    }
    return {"notes": notes, "details": details, "graph": graph_snapshot}


def git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout.strip()


def write_notes(server: Backend) -> tuple[dict, dict]:
    payloads = [
        ("notes/decision.md", "---\nproject: reinstall-proof\n---\n# Decision\n\nA durable choice. #memory\n\nSee [[notes/research|the research]].\n"),
        ("notes/research.md", "---\nsource: local\n---\n# Research\n\nEvidence for the choice.\n\nRelated [[notes/decision]].\n"),
        ("notes/rollback.md", "---\ncategory: recovery\n---\n# Rollback\n\nInitial wording.\n"),
    ]
    for path, body in payloads:
        server.request("PUT", "/api/memory/note", {"path": path, "body": body, "author": "owner"})

    claim = server.request("POST", "/api/claims", {
        "kind": "bug", "summary": "Reinstall proof sample claim",
        "evidence": "Seed data for the memory reinstall check.", "attempts_made": 1,
    })

    edited = server.request("PUT", "/api/memory/note", {
        "path": "notes/rollback.md", "body": "# Rollback\n\nEdited wording before reinstall.\n", "author": "owner",
    })
    return claim, edited


def main() -> int:
    rows: list[tuple[str, str, float]] = []
    with tempfile.TemporaryDirectory(prefix="glacier-memory-reinstall-") as temp_name:
        temp = Path(temp_name)
        first_home = temp / "first-home"
        fresh_home = temp / "fresh-home"
        bare = temp / "memory-remote.git"
        first = Backend(first_home)
        second = Backend(fresh_home)
        try:
            seeded = {}

            def seed():
                first.start()
                seeded["claim"], seeded["edit"] = write_notes(first)

            timed(rows, "Start backend + write notes/claim/edit", seed)
            # Capture identifiers and a saved version for the undo assertion from the API history.
            # The edit commit is the latest note history entry, so undo it after restore.
            snapshot = note_snapshot(first)
            history = first.request("GET", "/api/memory/history?path=notes%2Frollback.md")
            if not history or len(history) < 2:
                raise ProofFailure("Undo proof needs the original and edited versions")

            def push_remote():
                git("init", "--bare", str(bare))
                git("-C", str(first_home / "vault"), "remote", "add", "proof", str(bare))
                git("-C", str(first_home / "vault"), "push", "proof", "HEAD:refs/heads/main")
                first.stop()

            timed(rows, "Push vault history to local bare remote", push_remote)

            def delete_home():
                shutil.rmtree(first_home)
                if first_home.exists():
                    raise ProofFailure("Old GLACIER_HOME still exists")

            timed(rows, "Delete entire GLACIER_HOME", delete_home)

            def clone_and_start():
                fresh_home.mkdir(parents=True)
                git("clone", "--branch", "main", str(bare), str(fresh_home / "vault"))
                second.start()
                # Indexes are derived state. Rebuild FTS and link rows from the cloned Markdown
                # without writing new notes or commits into the restored Git history.
                import sqlite3
                if str(BACKEND) not in sys.path:
                    sys.path.insert(0, str(BACKEND))
                import memory_meta

                db_path = fresh_home / "vault" / ".index.sqlite"
                db = sqlite3.connect(db_path)
                db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(path UNINDEXED, body)")
                db.execute("CREATE TABLE IF NOT EXISTS links(src TEXT, dst TEXT)")
                db.execute("DELETE FROM fts")
                db.execute("DELETE FROM links")
                for path in sorted(p for p in (fresh_home / "vault").rglob("*.md") if ".git" not in p.parts):
                    rel = path.relative_to(fresh_home / "vault").as_posix()
                    raw = path.read_text(encoding="utf-8")
                    body = memory_meta.parse(raw, rel)[1]
                    db.execute("INSERT INTO fts VALUES (?,?)", (rel, body))
                    for target in re.findall(r"\[\[([^\]]+)\]\]", body):
                        db.execute("INSERT INTO links VALUES (?,?)", (rel, target.split("|", 1)[0].strip().removesuffix(".md")))
                db.commit()
                db.close()

            timed(rows, "Clone remote into fresh home + rebuild index", clone_and_start)
            def compare_snapshot():
                restored = note_snapshot(second)
                if restored != snapshot:
                    raise ProofFailure("Memory list, note bodies/links, or graph changed after reinstall")

            timed(rows, "Compare Memory list, bodies, links + graph", compare_snapshot)

            def compare_claim():
                claim_files = sorted((fresh_home / "vault" / "claims").glob("*.md"))
                if len(claim_files) != 1 or claim_files[0].name != Path(seeded["claim"]["path"]).name:
                    raise ProofFailure(f"Expected restored claim {seeded['claim']['path']}; found {claim_files}")
                claim_result = second.request("GET", "/api/claims")
                if len(claim_result) != 1 or claim_result[0]["kind"] != "bug" or claim_result[0]["summary"] != "Reinstall proof sample claim":
                    raise ProofFailure("Restored claim is not visible through the claims API")

            timed(rows, "Claim survives and remains readable", compare_claim)

            # Compare and exercise undo on the restored Git history; undo must reveal the prior body.
            def prove_undo():
                restored_history = second.request("GET", "/api/memory/history?path=notes%2Frollback.md")
                if len(restored_history) < 2:
                    raise ProofFailure("Restored undo history is missing")
                second.request("POST", "/api/memory/undo", {"path": "notes/rollback.md"})
                undone = second.request("GET", "/api/memory/note?path=notes%2Frollback.md")
                if "Initial wording." not in undone["body"]:
                    raise ProofFailure("Undo after reinstall did not restore the original body")

            timed(rows, "Undo history works after reinstall", prove_undo)

            def prove_compatibility():
                compatibility = second.request("GET", "/api/memory/compat")
                if not compatibility.get("ok"):
                    raise ProofFailure("Markdown conformance failed: " + json.dumps(compatibility.get("problems", [])))

            timed(rows, "Markdown conformance checker", prove_compatibility)
        except Exception as exc:
            print(f"Proof stopped: {exc}", file=sys.stderr)
            for server in (first, second):
                try:
                    server.stop()
                except Exception:
                    pass
            print_table(rows, failed=True)
            return 1
        finally:
            first.stop()
            second.stop()

    print_table(rows)
    return 0


def print_table(rows, failed=False):
    print("\nMemory reinstall proof")
    print("| Check | Result | Time |")
    print("|---|---:|---:|")
    for label, result, seconds in rows:
        print(f"| {label} | {result} | {seconds:.2f} s |")
    print(f"| Overall | {'FAIL' if failed else 'PASS'} | |")


if __name__ == "__main__":
    raise SystemExit(main())
