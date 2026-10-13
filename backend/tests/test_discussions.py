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


def test_parallel_discussion_lifecycle_and_edit(client):
    # Create parallel discussion with 2 providers
    create_resp = client.post("/api/discussions", json={
        "query": "Jelaskan perbedaan RAM dan SSD.",
        "mode": "parallel",
        "selected_providers": ["chatgpt", "gemini"]
    })
    assert create_resp.status_code == 201
    run = create_resp.json()
    run_id = run["id"]
    assert run["mode"] == "parallel"
    assert run["status"] == "awaiting_input"
    assert len(run["responses"]) == 2

    r1, r2 = run["responses"][0], run["responses"][1]
    assert r1["status"] == "pending"
    assert r2["status"] == "pending"

    # Fill first response
    res1 = client.post(f"/api/discussions/{run_id}/responses", json={
        "response_id": r1["id"],
        "content": "RAM adalah memori volatile berkecepatan tinggi.",
        "status": "completed"
    })
    assert res1.status_code == 200
    run_check1 = client.get(f"/api/discussions/{run_id}").json()
    assert run_check1["status"] == "awaiting_input"

    # Fill second response -> run completes
    res2 = client.post(f"/api/discussions/{run_id}/responses", json={
        "response_id": r2["id"],
        "content": "SSD adalah media penyimpanan nonvolatile berkapasitas besar.",
        "status": "completed"
    })
    assert res2.status_code == 200
    run_check2 = client.get(f"/api/discussions/{run_id}").json()
    assert run_check2["status"] == "completed"

    # Editing an existing response in completed parallel mode is allowed
    edit_res = client.post(f"/api/discussions/{run_id}/responses", json={
        "response_id": r1["id"],
        "content": "RAM adalah memori volatile berkecepatan ultra-tinggi untuk CPU.",
        "status": "completed"
    })
    assert edit_res.status_code == 200
    assert "ultra-tinggi" in edit_res.json()["content"]


def test_parallel_discussion_rejects_advance_endpoint(client):
    create_resp = client.post("/api/discussions", json={
        "query": "Apa keuntungan menggunakan containerization?",
        "mode": "parallel",
        "selected_providers": ["chatgpt", "claude"]
    })
    run_id = create_resp.json()["id"]

    # Attempting to call advance on parallel discussion must return 400
    adv_res = client.post(f"/api/discussions/{run_id}/advance")
    assert adv_res.status_code == 400
    detail = adv_res.json()["detail"].lower()
    assert "parallel" in detail
    assert "tidak memiliki alur advance debat" in detail


def test_continue_parallel_to_debate(client):
    # 1. Create and complete a parallel discussion
    create_resp = client.post("/api/discussions", json={
        "query": "Jelaskan perbedaan RAM dan SSD dalam tiga poin.",
        "mode": "parallel",
        "selected_providers": ["chatgpt", "gemini"]
    })
    par_run = create_resp.json()
    par_run_id = par_run["id"]

    for r in par_run["responses"]:
        client.post(f"/api/discussions/{par_run_id}/responses", json={
            "response_id": r["id"],
            "content": f"Jawaban dari {r['provider']} untuk perbandingan RAM dan SSD.",
            "status": "completed"
        })

    # 2. Continue to AI Debate
    cont_res = client.post(f"/api/discussions/{par_run_id}/continue-to-debate")
    assert cont_res.status_code == 201
    debate_run = cont_res.json()
    debate_id = debate_run["id"]

    assert debate_id != par_run_id
    assert debate_run["mode"] == "debate"
    assert debate_run["current_stage"] == "initial_analysis"
    assert debate_run["current_round"] == 1
    assert debate_run["max_rounds"] <= 3
    assert len(debate_run["responses"]) == 2

    # Verify answers were carried over into initial analysis
    for dr in debate_run["responses"]:
        assert dr["stage"] == "initial_analysis"
        assert dr["status"] == "completed"
        assert f"Jawaban dari {dr['provider']}" in dr["content"]

    # Since all initial responses are completed, debate can immediately advance to cross-critique
    adv_res = client.post(f"/api/discussions/{debate_id}/advance")
    assert adv_res.status_code == 200
    adv_data = adv_res.json()
    assert adv_data["current_stage"] == "cross_critique"

    # 3. Verify original parallel run remains untouched and completed
    original_check = client.get(f"/api/discussions/{par_run_id}").json()
    assert original_check["mode"] == "parallel"
    assert original_check["status"] == "completed"
    assert len(original_check["responses"]) == 2

    # 4. Verify report export (both markdown and txt formats)
    export_md = client.get(f"/api/discussions/{par_run_id}/export")
    assert export_md.status_code == 200
    assert "Analisis Mandiri Dewan AI" in export_md.text
    assert "Jawaban dari chatgpt" in export_md.text
    assert "text/markdown" in export_md.headers.get("content-type", "")
    assert f'filename="ai_council_report_{par_run_id[:8]}.md"' in export_md.headers.get("content-disposition", "")

    export_txt = client.get(f"/api/discussions/{par_run_id}/export?format=txt")
    assert export_txt.status_code == 200
    assert "Analisis Mandiri Dewan AI" in export_txt.text
    assert "text/plain" in export_txt.headers.get("content-type", "")
    assert f'filename="ai_council_report_{par_run_id[:8]}.txt"' in export_txt.headers.get("content-disposition", "")

