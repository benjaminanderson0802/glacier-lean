import httpx


def test_only_the_desktop_app_may_call_cross_origin(server):
    ok = httpx.options(server.url + "/api/environments", headers={"Origin": "http://tauri.localhost", "Access-Control-Request-Method": "GET"}, timeout=30)
    assert ok.headers.get("access-control-allow-origin") == "http://tauri.localhost"
    bad = httpx.get(server.url + "/api/environments", headers={"Origin": "https://evil.example"}, timeout=30)
    assert "access-control-allow-origin" not in bad.headers
