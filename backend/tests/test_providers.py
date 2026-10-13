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
    assert "notebooklm" in provider_ids

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
    assert "Mode Manual Bridge" in test_data["message"]


def test_notebooklm_cannot_set_api_mode(client):
    res = client.put("/api/providers/notebooklm", json={
        "default_mode": "api"
    })
    assert res.status_code == 400
    assert "tidak menyediakan api publik" in res.json()["detail"].lower()


