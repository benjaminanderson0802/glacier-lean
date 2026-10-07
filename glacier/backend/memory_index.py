"""Local meaning search over markdown notes, stored as a disposable sqlite-vec index."""

import json
import os
import re
import sqlite3
import urllib.error
import urllib.request

import sqlite_vec


_DB_NAME = "memory_index.sqlite"
_TABLE = "meaning_vectors"
_MAX_CHUNK = 800


def _home():
    return os.path.abspath(os.environ.get("GLACIER_HOME", "data"))


def _connect():
    os.makedirs(_home(), exist_ok=True)
    connection = sqlite3.connect(os.path.join(_home(), _DB_NAME), timeout=30)
    sqlite_vec.load(connection)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS meaning_chunks "
        "(id INTEGER PRIMARY KEY, path TEXT NOT NULL, content TEXT NOT NULL)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS meaning_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    return connection


def _embed(texts):
    if not texts:
        return []
    base_url = os.environ.get("GLACIER_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("GLACIER_EMBED_MODEL", "all-minilm")
    payload = json.dumps({"model": model, "input": texts}).encode("utf-8")
    request = urllib.request.Request(
        base_url + "/api/embed", data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        vectors = result.get("embeddings")
        if vectors is None and len(texts) == 1 and "embedding" in result:
            vectors = [result["embedding"]]
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise ValueError("Ollama returned an unexpected number of embeddings")
        vectors = [[float(value) for value in vector] for vector in vectors]
        if not vectors or not vectors[0] or any(len(vector) != len(vectors[0]) for vector in vectors):
            raise ValueError("Ollama returned invalid embedding dimensions")
        return vectors
    except Exception as exc:
        raise RuntimeError(f"meaning search unavailable: {exc}") from exc


def _chunks(text):
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks = []
    for paragraph in paragraphs:
        while len(paragraph) > _MAX_CHUNK:
            # Prefer a word boundary, while ensuring progress for long unbroken text.
            split_at = paragraph.rfind(" ", 0, _MAX_CHUNK + 1)
            if split_at < 1:
                split_at = _MAX_CHUNK
            chunks.append(paragraph[:split_at].strip())
            paragraph = paragraph[split_at:].strip()
        if paragraph:
            chunks.append(paragraph)
    return chunks


def _notes(vault_dir):
    vault_dir = os.path.abspath(vault_dir)
    for root, dirs, files in os.walk(vault_dir):
        dirs[:] = sorted(d for d in dirs if d != ".git" and not d.startswith("."))
        for filename in sorted(files):
            if not filename.endswith(".md"):
                continue
            full_path = os.path.join(root, filename)
            relative = os.path.relpath(full_path, vault_dir).replace(os.sep, "/")
            with open(full_path, encoding="utf-8") as note:
                yield relative, _chunks(note.read())


def _ensure_vectors(connection, dimension):
    stored = connection.execute("SELECT value FROM meaning_settings WHERE key='dimension'").fetchone()
    if stored and int(stored[0]) != dimension:
        connection.execute(f"DROP TABLE IF EXISTS {_TABLE}")
        connection.execute("DELETE FROM meaning_chunks")
        connection.execute("DELETE FROM meaning_settings WHERE key='dimension'")
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (_TABLE,)
    ).fetchone()
    if not exists:
        connection.execute(f"CREATE VIRTUAL TABLE {_TABLE} USING vec0(embedding float[{dimension}])")
        connection.execute(
            "INSERT OR REPLACE INTO meaning_settings(key, value) VALUES ('dimension', ?)",
            (str(dimension),),
        )


def _replace_note(connection, path, chunks, vectors):
    old_ids = [row[0] for row in connection.execute("SELECT id FROM meaning_chunks WHERE path=?", (path,))]
    for row_id in old_ids:
        connection.execute(f"DELETE FROM {_TABLE} WHERE rowid=?", (row_id,))
    connection.execute("DELETE FROM meaning_chunks WHERE path=?", (path,))
    for content, vector in zip(chunks, vectors):
        cursor = connection.execute(
            "INSERT INTO meaning_chunks(path, content) VALUES (?, ?)", (path, content)
        )
        connection.execute(
            f"INSERT INTO {_TABLE}(rowid, embedding) VALUES (?, ?)",
            (cursor.lastrowid, sqlite_vec.serialize_float32(vector)),
        )


def rebuild(vault_dir):
    """Recreate the index from markdown files and return the number of notes indexed."""
    notes = list(_notes(vault_dir))
    flat_chunks = [(path, chunk) for path, chunks in notes for chunk in chunks]
    vectors = _embed([chunk for _, chunk in flat_chunks])
    connection = _connect()
    try:
        connection.execute("BEGIN")
        connection.execute("DELETE FROM meaning_chunks")
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (_TABLE,)
        ).fetchone()
        dimension = len(vectors[0]) if vectors else None
        if dimension:
            _ensure_vectors(connection, dimension)
            connection.execute(f"DELETE FROM {_TABLE}")
            grouped = {}
            for (path, chunk), vector in zip(flat_chunks, vectors):
                grouped.setdefault(path, ([], []))[0].append(chunk)
                grouped[path][1].append(vector)
            for path, (chunks, note_vectors) in grouped.items():
                _replace_note(connection, path, chunks, note_vectors)
        elif exists:
            connection.execute(f"DELETE FROM {_TABLE}")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return len(notes)


def update(vault_dir, path):
    """Replace one note's indexed chunks, or remove them when the note was deleted."""
    vault_dir = os.path.abspath(vault_dir)
    path = os.fspath(path)
    if os.path.isabs(path):
        path = os.path.relpath(path, vault_dir)
    path = path.replace(os.sep, "/")
    full_path = os.path.abspath(os.path.join(vault_dir, path))
    if os.path.commonpath([vault_dir, full_path]) != vault_dir:
        raise ValueError(f"bad memory path: {path}")
    chunks = []
    if os.path.isfile(full_path) and full_path.endswith(".md"):
        with open(full_path, encoding="utf-8") as note:
            chunks = _chunks(note.read())
    vectors = _embed(chunks)
    connection = _connect()
    try:
        connection.execute("BEGIN")
        if vectors:
            _ensure_vectors(connection, len(vectors[0]))
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (_TABLE,)
        ).fetchone()
        if exists:
            _replace_note(connection, path, chunks, vectors)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def search(q, k=10):
    """Return (relative note path, similarity score) pairs, best chunk per note."""
    if k <= 0:
        return []
    query_vector = _embed([q])[0]
    connection = _connect()
    try:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (_TABLE,)
        ).fetchone()
        if not exists:
            return []
        dimension = connection.execute(
            "SELECT value FROM meaning_settings WHERE key='dimension'"
        ).fetchone()
        if dimension and int(dimension[0]) != len(query_vector):
            return []
        scores = {}
        rows = connection.execute(
            f"SELECT c.path, 1.0 - vec_distance_cosine(v.embedding, ?) "
            f"FROM {_TABLE} AS v JOIN meaning_chunks AS c ON c.id=v.rowid",
            (sqlite_vec.serialize_float32(query_vector),),
        )
        for path, score in rows:
            scores[path] = max(scores.get(path, float("-inf")), float(score))
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]
    finally:
        connection.close()
