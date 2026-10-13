import pytest


def test_create_parallel_discussion(client):
    payload = {
        "query": "Apa perbedaan utama antara arsitektur REST dan GraphQL?",
        "mode": "parallel",
        "selected_providers": ["chatgpt", "claude", "gemini"]
    }
    response = client.post("/api/discussions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["mode"] == "parallel"
    assert data["status"] == "awaiting_input"
    assert len(data["responses"]) == 3
    # Check that prompts are generated and status is pending (Manual Bridge)
    for r in data["responses"]:
        assert r["status"] == "pending"
        assert r["integration_mode"] == "manual"
        assert "REST" in r["prompt_used"]


def test_submit_manual_response(client):
    # 1. Create run
    create_resp = client.post("/api/discussions", json={
        "query": "Jelaskan konsep zero-trust security.",
        "mode": "parallel",
        "selected_providers": ["chatgpt", "claude"]
    })
    run_data = create_resp.json()
    target_response_id = run_data["responses"][0]["id"]

    # 2. Submit manual response
    submit_payload = {
        "response_id": target_response_id,
        "content": "Zero-trust adalah paradigma keamanan yang berasumsi tidak ada entitas internal maupun eksternal yang dipercaya secara default.",
        "model_id": "GPT-4o Manual",
        "status": "completed"
    }
    resp = client.post(f"/api/discussions/{run_data['id']}/responses", json=submit_payload)
    assert resp.status_code == 200
    updated_resp = resp.json()
    assert updated_resp["status"] == "completed"
    assert "Zero-trust" in updated_resp["content"]
    assert updated_resp["completion_tokens"] > 0
