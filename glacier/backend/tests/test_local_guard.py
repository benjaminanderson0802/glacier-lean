import httpx


BLOCKED = "This request came from another website and was blocked."


def test_cross_site_origin_post_is_blocked(server):
    response = httpx.post(server.url + "/api/environments/demo/run",
                          headers={"Origin": "https://evil.example"}, timeout=30)
    assert response.status_code == 403
    assert response.json()["detail"] == BLOCKED


def test_same_origin_and_tauri_origins_are_allowed(server):
    for origin in (server.url, "http://localhost:5173", "http://127.0.0.1:4173",
                   "http://tauri.localhost", "tauri://localhost", "https://tauri.localhost"):
        response = httpx.put(server.url + "/api/environments/demo",
                             headers={"Origin": origin}, json={"nodes": [], "edges": []}, timeout=30)
        assert response.status_code != 403, origin


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
