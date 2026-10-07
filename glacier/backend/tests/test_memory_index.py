import json
import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import memory_index


VOCABULARY = ["refund", "billing", "invoice", "pizza", "cheese", "orbit", "planet", "rocket"]
EMBED_BATCHES = []


class _EmbedHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/embed":
            self.send_error(404)
            return
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        inputs = request.get("input", request.get("prompt", []))
        if isinstance(inputs, str):
            inputs = [inputs]
        EMBED_BATCHES.append((request.get("model"), len(inputs)))
        embeddings = []
        for value in inputs:
            words = value.lower().split()
            embeddings.append([float(sum(word.strip(".,!?;:") == term for word in words)) for term in VOCABULARY])
        body = json.dumps({"embeddings": embeddings}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


@pytest.fixture
def embed_server(monkeypatch, tmp_path):
    connection = sqlite3.connect(":memory:")
    try:
        memory_index.sqlite_vec.load(connection)
    except Exception as exc:
        pytest.skip(f"Meaning search needs SQLite vector support, but the extension cannot load: {exc}")
        raise
    finally:
        connection.close()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _EmbedHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("GLACIER_OLLAMA_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("GLACIER_EMBED_MODEL", "test-bag-of-words")
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    yield tmp_path
    server.shutdown()
    thread.join()
    server.server_close()


def _put(vault, path, body):
    target = vault / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def test_connect_reports_vector_extension_load_error_as_runtime_error(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    monkeypatch.setattr(memory_index.sqlite_vec, "load", lambda _connection: (_ for _ in ()).throw(sqlite3.OperationalError("not authorized")))

    with pytest.raises(RuntimeError, match="vector search is unavailable"):
        memory_index._connect()


def test_meaning_search_ranks_closest_note_first(embed_server, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    _put(vault, "food.md", "Pizza with cheese makes a good dinner.")
    _put(vault, "billing.md", "Refund the invoice for the billing issue.")

    assert memory_index.rebuild(str(vault)) == 2
    results = memory_index.search("I need money back for an invoice", k=10)

    assert results[0][0] == "billing.md"


def test_update_replaces_changed_note_embedding(embed_server, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "topic.md"
    _put(vault, "topic.md", "A refund appears on the invoice.")
    _put(vault, "other.md", "Pizza with cheese for dinner.")
    memory_index.rebuild(str(vault))

    note.write_text("A rocket travels around a planet.", encoding="utf-8")
    memory_index.update(str(vault), "topic.md")

    assert memory_index.search("planet and rocket", k=1)[0][0] == "topic.md"
    assert memory_index.search("refund invoice", k=1)[0][0] == "other.md"


def test_incremental_index_matches_fresh_rebuild(embed_server, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    _put(vault, "one.md", "Refund the billing invoice.")
    _put(vault, "two.md", "A rocket visits a planet.")
    memory_index.rebuild(str(vault))
    _put(vault, "one.md", "Pizza with cheese for dinner.")
    memory_index.update(str(vault), "one.md")
    incremental = memory_index.search("cheese pizza", k=10)

    db_path = tmp_path / "memory_index.sqlite"
    db_path.unlink()
    assert memory_index.rebuild(str(vault)) == 2
    assert memory_index.search("cheese pizza", k=10) == incremental


def test_deleted_index_is_rebuilt_from_markdown(embed_server, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    _put(vault, "one.md", "Refund the billing invoice.")
    _put(vault, "two.md", "Pizza with cheese for dinner.")
    memory_index.rebuild(str(vault))
    expected = memory_index.search("invoice refund", k=10)
    (tmp_path / "memory_index.sqlite").unlink()

    assert memory_index.rebuild(str(vault)) == 2
    assert memory_index.search("invoice refund", k=10) == expected


def test_unavailable_ollama_raises_documented_error(monkeypatch, tmp_path):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    monkeypatch.setenv("GLACIER_OLLAMA_URL", "http://127.0.0.1:1")
    vault = tmp_path / "vault"
    vault.mkdir()
    _put(vault, "one.md", "Some note text.")

    with pytest.raises(RuntimeError, match=r"^meaning search unavailable: .+"):
        memory_index.rebuild(str(vault))


def test_search_without_index_reports_no_index(embed_server):
    with pytest.raises(RuntimeError, match=r"^meaning search unavailable: no index yet$"):
        memory_index.search("anything")


def test_model_change_rebuilds_index_automatically(embed_server, tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    _put(vault, "one.md", "Refund the billing invoice.")
    _put(vault, "two.md", "Pizza with cheese for dinner.")
    memory_index.rebuild(str(vault))

    monkeypatch.setenv("GLACIER_EMBED_MODEL", "changed-test-model")
    assert memory_index.search("refund invoice", k=1)[0][0] == "one.md"
    _put(vault, "two.md", "A rocket visits a planet.")
    memory_index.update(str(vault), "two.md")
    assert memory_index.search("rocket planet", k=1)[0][0] == "two.md"
    assert memory_index.search("pizza cheese", k=1)[0][0] == "one.md"
    import sqlite3
    with sqlite3.connect(tmp_path / "memory_index.sqlite") as connection:
        assert connection.execute(
            "SELECT value FROM meaning_settings WHERE key='model'"
        ).fetchone() == ("changed-test-model",)


def test_rebuild_embeds_chunks_in_batches_of_64(embed_server, tmp_path):
    EMBED_BATCHES.clear()
    vault = tmp_path / "vault"
    vault.mkdir()
    for number in range(130):
        _put(vault, f"{number:03}.md", "Refund the billing invoice.")

    assert memory_index.rebuild(str(vault)) == 130
    assert [count for model, count in EMBED_BATCHES] == [64, 64, 2]


def test_bad_utf8_bytes_do_not_break_rebuild(embed_server, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "bad.md").write_bytes(b"Refund invoice \xff\xfe")

    assert memory_index.rebuild(str(vault)) == 1
