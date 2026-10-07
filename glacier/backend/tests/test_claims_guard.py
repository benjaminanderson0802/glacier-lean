import httpx
import mem_server
import pytest


@pytest.mark.parametrize("path", ["Claims/forged.md", "CLAIMS/x.md", "claims\\x.md", "./Claims/x.md"])
def test_claims_cannot_be_written_through_memory_in_any_spelling(server, path):
    r = httpx.put(server.url + "/api/memory/note", json={"path": path, "body": "forged", "author": "owner"}, timeout=30)
    assert r.status_code == 400, (path, r.status_code, r.text)


def test_mcp_refuses_claims_in_any_spelling(tmp_path):
    import vault
    vault.init(str(tmp_path / "vault"))
    for path in ("Claims/forged.md", "claims\\x.md"):
        with pytest.raises(ValueError):
            mem_server._validate_worker_write(path, "worker:x", "")
