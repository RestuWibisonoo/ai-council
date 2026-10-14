import pytest


def test_list_and_update_providers(client):
    # 1. List seeded providers
    res = client.get("/api/providers")
    assert res.status_code == 200
    providers = res.json()
    assert len(providers) >= 4
    provider_ids = [p["id"] for p in providers]
    assert "chatgpt" in provider_ids
    assert "claude" in provider_ids
    assert "gemini" in provider_ids
    # NotebookLM is a manual-only web app and must not be in provider list
    assert "notebooklm" not in provider_ids

    # All providers must operate in API mode (no Manual Bridge)
    for p in providers:
        assert p["default_mode"] == "api", f"Provider {p['id']} should have default_mode='api'"

    # 2. Update provider settings (model selection and monthly limit)
    update_res = client.put("/api/providers/chatgpt", json={
        "selected_model": "gpt-4o-mini",
        "usage_limit_monthly_usd": 50.0
    })
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["selected_model"] == "gpt-4o-mini"
    assert updated["usage_limit_monthly_usd"] == 50.0

    # 3. Test unconfigured provider without API key
    test_res = client.post("/api/providers/chatgpt/test", json={})
    assert test_res.status_code == 200
    test_data = test_res.json()
    assert test_data["success"] is False
    assert "belum dikonfigurasi" in test_data["message"].lower() or "belum diisi" in test_data["message"].lower()
    assert "manual" not in test_data["message"].lower()


def test_manual_mode_is_rejected(client):
    """Verifies that attempting to configure Manual Bridge is rejected."""
    res = client.put("/api/providers/chatgpt", json={
        "default_mode": "manual"
    })
    assert res.status_code == 400
    assert "manual bridge telah dihapus" in res.json()["detail"].lower()


def test_notebooklm_is_rejected_in_discussion_and_config(client):
    """Verifies that NotebookLM (manual-only) cannot be used in discussions or configured."""
    res = client.put("/api/providers/notebooklm", json={
        "default_mode": "api"
    })
    assert res.status_code in (400, 404)

    # Creating a discussion with notebooklm must fail
    res_disc = client.post("/api/discussions", json={
        "query": "Uji penolakan manual NotebookLM",
        "mode": "parallel",
        "selected_providers": ["notebooklm"]
    })
    assert res_disc.status_code == 400
    assert "notebooklm" in res_disc.json()["detail"].lower()
