import httpx


BLOCKED = "This request came from another website and was blocked."


def test_cross_site_origin_post_is_blocked(server):
    response = httpx.post(server.url + "/api/environments/demo/run",
                          headers={"Origin": "https://evil.example"}, timeout=30)
    assert response.status_code == 403
    assert response.json()["detail"] == BLOCKED


def test_same_origin_and_tauri_origins_are_allowed(server):
    for origin in (server.url, "http://tauri.localhost", "tauri://localhost", "https://tauri.localhost"):
        response = httpx.put(server.url + "/api/environments/demo",
                             headers={"Origin": origin}, json={"nodes": [], "edges": []}, timeout=30)
        assert response.status_code != 403, origin


def test_dev_screen_origin_without_dev_mode_is_blocked(server):
    import os
    os.environ.pop("GLACIER_DEV", None)
    response = httpx.put(server.url + "/api/environments/demo",
                         headers={"Origin": "http://localhost:5173"}, json={"nodes": [], "edges": []}, timeout=30)
    assert response.status_code == 403


def test_dev_screen_origins_require_dev_mode(make_server, monkeypatch):
    import os
    monkeypatch.setenv("GLACIER_DEV", "1")
    server = make_server().start()
    try:
        for origin in ("http://localhost:5173", "http://127.0.0.1:4173"):
            response = httpx.put(server.url + "/api/environments/demo",
                                 headers={"Origin": origin}, json={"nodes": [], "edges": []}, timeout=30)
            assert response.status_code != 403, origin
    finally:
        server.stop()


def test_explicit_dev_origin_allow_list_is_loopback_only(make_server, monkeypatch):
    monkeypatch.setenv("GLACIER_DEV", "1")
    monkeypatch.setenv("GLACIER_DEV_ORIGINS", "http://localhost:5187, http://127.0.0.1:4187")
    server = make_server().start()
    try:
        for origin in ("http://localhost:5187", "http://127.0.0.1:4187"):
            response = httpx.put(server.url + "/api/environments/demo",
                                 headers={"Origin": origin}, json={"nodes": [], "edges": []}, timeout=30)
            assert response.status_code != 403, origin

        for origin in ("https://evil.example", "http://evil.example:5187", "http://localhost:5188",
                       "https://localhost:5187", "http://user@localhost:5187"):
            response = httpx.put(server.url + "/api/environments/foreign",
                                 headers={"Origin": origin}, json={"nodes": [], "edges": []}, timeout=30)
            assert response.status_code == 403, origin
    finally:
        server.stop()


def test_foreign_origin_remains_blocked_with_dev_mode_enabled(server, monkeypatch):
    monkeypatch.setenv("GLACIER_DEV", "1")
    monkeypatch.setenv("GLACIER_DEV_ORIGINS", "http://localhost:5187")
    response = httpx.post(server.url + "/api/environments/demo/run",
                          headers={"Origin": "https://evil.example"}, timeout=30)
    assert response.status_code == 403
    assert response.json()["detail"] == BLOCKED


def test_headerless_curl_style_post_is_allowed(server):
    response = httpx.post(server.url + "/api/environments/demo/run", timeout=30)
    assert response.status_code == 404


def test_cross_site_fetch_without_origin_is_blocked(server):
    response = httpx.post(server.url + "/api/environments/demo/run",
                          headers={"Sec-Fetch-Site": "cross-site"}, timeout=30)
    assert response.status_code == 403
    assert response.json()["detail"] == BLOCKED


def test_dns_rebinding_host_is_blocked(server):
    response = httpx.get(server.url + "/api/environments", headers={"Host": "glacier.attacker.example"}, timeout=30)
    assert response.status_code == 403


def test_form_content_type_on_json_endpoint_is_blocked(server):
    response = httpx.put(server.url + "/api/environments/demo",
                         content="name=forged", headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    assert response.status_code == 415


def test_trusted_multipart_import_is_not_refused_as_form(server):
    response = httpx.post(server.url + "/api/imports", files={"file": ("flow.json", b"{}", "application/json")},
                          headers={"Origin": server.url}, timeout=30)
    assert response.status_code != 415


def test_hostile_websocket_origin_is_rejected(server):
    import asyncio
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from local_guard import LocalRequestGuard

    sent = []
    accepted = False

    async def app(scope, receive, send):
        nonlocal accepted
        accepted = True
        await send({"type": "websocket.accept"})

    async def receive():
        return {"type": "websocket.connect"}

    async def send(message):
        sent.append(message)

    for headers in ([ (b"host", b"127.0.0.1:8000"), (b"origin", b"https://evil.example") ],
                    [ (b"host", b"evil.example"), (b"origin", b"http://localhost:8000") ]):
        sent.clear()
        accepted = False
        scope = {"type": "websocket", "asgi": {"version": "3.0"}, "scheme": "ws", "path": "/api/events",
                 "raw_path": b"/api/events", "query_string": b"", "headers": headers,
                 "server": ("127.0.0.1", 8000), "client": ("127.0.0.1", 1)}
        asyncio.run(LocalRequestGuard(app)(scope, receive, send))
        assert not accepted
        assert sent == [{"type": "websocket.close", "code": 1008}]
