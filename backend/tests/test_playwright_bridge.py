from app.services.playwright_bridge import PROVIDERS


def test_bridge_only_targets_known_official_provider_hosts():
    assert set(PROVIDERS) == {"chatgpt", "gemini", "claude", "notebooklm"}
    assert PROVIDERS["chatgpt"]["url"].startswith("https://chatgpt.com/")
    assert PROVIDERS["gemini"]["url"].startswith("https://gemini.google.com/")
    assert PROVIDERS["claude"]["url"].startswith("https://claude.ai/")
    assert PROVIDERS["notebooklm"]["url"].startswith("https://notebooklm.google.com/")


def test_bridge_has_editors_for_supported_providers():
    for provider in PROVIDERS.values():
        assert provider["selectors"]
        assert all(isinstance(selector, str) and selector for selector in provider["selectors"])


def test_playwright_bridge_status_endpoint(client):
    res = client.get("/api/playwright-bridge/status")
    assert res.status_code == 200
    data = res.json()
    assert "active" in data
    assert data["submitted_automatically"] is False
    assert "playwright-profile" in data["profile_directory"]


def test_playwright_bridge_validation_endpoints(client):
    # Invalid provider
    res = client.post("/api/playwright-bridge/open-fill", json={
        "provider": "unknown_ai",
        "prompt": "Halo dunia"
    })
    assert res.status_code == 422

    # Empty prompt
    res2 = client.post("/api/playwright-bridge/open-fill", json={
        "provider": "chatgpt",
        "prompt": ""
    })
    assert res2.status_code == 422


def test_playwright_bridge_rejects_external_ip():
    from starlette.testclient import TestClient
    from app.main import app

    # Create client simulating non-loopback LAN host
    ext_client = TestClient(app, client=("192.168.1.100", 50000))
    res = ext_client.get("/api/playwright-bridge/status")
    assert res.status_code == 403
    assert "koneksi lokal" in res.json()["detail"].lower()

