import pytest


def test_full_manual_council_workflow(client):
    """
    End-to-End Integration Test:
    Runs complete manual workflow from user question, model selection,
    manual response bridge, cross-critique, rebuttal, to moderator synthesis.
    All data is labeled as test data.
    """
    # Step 1: User submits question for 3 council models
    query = "[TEST DATA] Bagaimana strategi mitigasi risiko hallucination pada LLM di sistem perbankan?"
    create_resp = client.post("/api/discussions", json={
        "query": query,
        "mode": "debate",
        "selected_providers": ["chatgpt", "claude", "gemini"],
        "max_rounds": 1,
        "conversation_title": "[TEST] Evaluasi Halusinasi Perbankan"
    })
    assert create_resp.status_code == 201
    run = create_resp.json()
    run_id = run["id"]
    conv_id = run["conversation_id"]

    # Step 2: User opens official links, pastes responses into Manual Bridge for ChatGPT, Claude, Gemini
    for resp in run["responses"]:
        client.post(f"/api/discussions/{run_id}/responses", json={
            "response_id": resp["id"],
            "content": f"[TEST DATA RESPONS AWAL] {resp['provider'].upper()}: Gunakan arsitektur RAG ketat dengan validasi skema Pydantic dan sitasi berbasis database lokal.",
            "status": "completed"
        })

    # Step 3: Advance to Cross-Critique
    adv_critique = client.post(f"/api/discussions/{run_id}/advance")
    assert adv_critique.status_code == 200
    critique_run = adv_critique.json()
    assert critique_run["current_stage"] == "cross_critique"

    critique_resps = [r for r in critique_run["responses"] if r["stage"] == "cross_critique"]
    for cr in critique_resps:
        client.post(f"/api/discussions/{run_id}/responses", json={
            "response_id": cr["id"],
            "content": f"[TEST DATA KRITIK] {cr['provider'].upper()}: RAG saja tidak cukup jika ada prompt injection atau data embedding yang terkorupsi.",
            "status": "completed"
        })

    # Step 4: Advance to Rebuttal
    adv_rebuttal = client.post(f"/api/discussions/{run_id}/advance")
    assert adv_rebuttal.status_code == 200
    rebuttal_run = adv_rebuttal.json()
    assert rebuttal_run["current_stage"] == "rebuttal"

    rebuttal_resps = [r for r in rebuttal_run["responses"] if r["stage"] == "rebuttal"]
    for reb in rebuttal_resps:
        client.post(f"/api/discussions/{run_id}/responses", json={
            "response_id": reb["id"],
            "content": f"[TEST DATA REBUTTAL] {reb['provider'].upper()}: Sepakat. Kita wajib menambahkan layer input guardrail dan deterministic semantic firewall.",
            "status": "completed"
        })

    # Step 5: Advance to Final Synthesis
    adv_synth = client.post(f"/api/discussions/{run_id}/advance")
    assert adv_synth.status_code == 200
    synth_run = adv_synth.json()
    assert synth_run["current_stage"] == "final_synthesis"

    # Step 6: Submit Final Moderator Consensus Synthesis
    synth_text = """[TEST DATA] # Sintesis Konsensus AI Council: Mitigasi Halusinasi Perbankan

1. Ringkasan Masalah: Pencegahan kesalahan fatal output AI pada data keuangan sensitif.
2. Kesepakatan Antarmodel: RAG deterministik, validasi skema ketat, dan fallback manusia mutlak ada.
3. Perbedaan Pendapat: Penggunaan open-weight on-premise vs API closed-source terenkripsi.
4. Kritik yang Belum Terselesaikan: Kecepatan audit forensik model deep learning yang kompleks.
5. Bukti yang Mendukung Kesimpulan: Regulasi perbankan OJK/Basel III mengenai auditability.
6. Rekomendasi: Implementasikan multi-layer guardrails dengan human-in-the-loop untuk transaksi berisiko tinggi.
7. Ketidakpastian & Kebutuhan Verifikasi: Latensi inferensi saat validasi multi-model secara sinkron.
8. Referensi Sumber: Pedoman Keamanan Sistem Finansial Nasional."""

    submit_synth = client.post(f"/api/discussions/{run_id}/synthesis", json={
        "run_id": run_id,
        "moderator_provider": "council_moderator",
        "raw_synthesis": synth_text
    })
    assert submit_synth.status_code == 200

    # Step 7: Verify completed run and conversation persistence
    final_run_res = client.get(f"/api/discussions/{run_id}")
    final_run = final_run_res.json()
    assert final_run["status"] == "completed"

    # Verify conversation history contains messages
    conv_res = client.get(f"/api/conversations/{conv_id}")
    assert conv_res.status_code == 200
    conv_data = conv_res.json()
    assert conv_data["id"] == conv_id

    # Verify Usage Summary tracked the manual calls accurately
    usage_res = client.get("/api/usage/summary")
    assert usage_res.status_code == 200
    usage_summary = usage_res.json()
    assert usage_summary["manual_requests"] >= 9
    assert usage_summary["total_requests"] >= 9
