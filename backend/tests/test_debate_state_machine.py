import pytest


def test_debate_state_machine_flow(client):
    # 1. Create debate
    init_res = client.post("/api/discussions", json={
        "query": "Haruskah tim engineering mengadopsi monorepo atau multirepo untuk skala enterprise?",
        "mode": "debate",
        "selected_providers": ["chatgpt", "claude"],
        "max_rounds": 1
    })
    assert init_res.status_code == 201
    run = init_res.json()
    run_id = run["id"]
    assert run["current_stage"] == "initial_analysis"

    # Fill initial answers for both
    resps = run["responses"]
    assert len(resps) == 2
    for r in resps:
        client.post(f"/api/discussions/{run_id}/responses", json={
            "response_id": r["id"],
            "content": f"Analisis awal dari {r['provider']}: Pendekatan kami menitikberatkan konsistensi dependensi.",
            "status": "completed"
        })

    # 2. Advance to Cross-Critique
    adv1 = client.post(f"/api/discussions/{run_id}/advance")
    assert adv1.status_code == 200
    adv1_data = adv1.json()
    assert adv1_data["current_stage"] == "cross_critique"

    # Fill critique answers
    critique_resps = [r for r in adv1_data["responses"] if r["stage"] == "cross_critique"]
    assert len(critique_resps) == 2
    for cr in critique_resps:
        client.post(f"/api/discussions/{run_id}/responses", json={
            "response_id": cr["id"],
            "content": f"Kritik dari {cr['provider']}: Solusi lawan mengabaikan overhead CI/CD pipeline yang membengkak.",
            "status": "completed"
        })

    # 3. Advance to Rebuttal
    adv2 = client.post(f"/api/discussions/{run_id}/advance")
    assert adv2.status_code == 200
    adv2_data = adv2.json()
    assert adv2_data["current_stage"] == "rebuttal"

    # Fill rebuttal answers
    rebuttal_resps = [r for r in adv2_data["responses"] if r["stage"] == "rebuttal"]
    assert len(rebuttal_resps) == 2
    for reb in rebuttal_resps:
        client.post(f"/api/discussions/{run_id}/responses", json={
            "response_id": reb["id"],
            "content": f"Tanggapan balik {reb['provider']}: Kami mengakui beban CI/CD, namun tooling caching modern menguranginya signifikan.",
            "status": "completed"
        })

    # 4. Advance to Final Synthesis (since max_rounds is 1)
    adv3 = client.post(f"/api/discussions/{run_id}/advance")
    assert adv3.status_code == 200
    adv3_data = adv3.json()
    assert adv3_data["current_stage"] == "final_synthesis"

    # 5. Submit moderator synthesis
    synth_payload = {
        "run_id": run_id,
        "moderator_provider": "council_moderator",
        "raw_synthesis": """# Sintesis Konsensus AI Council
1. Ringkasan Masalah: Pemilihan arsitektur repositori skala enterprise.
2. Kesepakatan Antarmodel: Kedua kubu sepakat tooling dan otomatisasi mutlak diperlukan.
3. Perbedaan Pendapat: Monorepo unggul di visibilitas kode, multirepo di isolasi akses.
4. Kritik yang Belum Terselesaikan: Skalabilitas git clone repository ukuran puluhan gigabyte.
5. Bukti yang Mendukung Kesimpulan: Pengalaman adopsi Google vs Amazon.
6. Rekomendasi: Gunakan monorepo dengan remote caching untuk layanan yang saling terkait erat.
7. Ketidakpastian & Kebutuhan Verifikasi: Ukuran tim dan kesiapan infrastruktur internal.
8. Referensi Sumber: Dokumentasi Nx dan Bazel."""
    }
    synth_res = client.post(f"/api/discussions/{run_id}/synthesis", json=synth_payload)
    assert synth_res.status_code == 200

    # Verify run completed
    final_run = client.get(f"/api/discussions/{run_id}").json()
    assert final_run["status"] == "completed"
    assert len(final_run["syntheses"]) == 1
    assert "Monorepo" in final_run["syntheses"][0]["raw_synthesis"]

    # Export report
    report_res = client.get(f"/api/discussions/{run_id}/export")
    assert report_res.status_code == 200
    assert "Laporan Hasil AI Council" in report_res.text


def test_invalid_advance_without_responses(client):
    """Cannot advance to critique when no initial responses have been filled."""
    init_res = client.post("/api/discussions", json={
        "query": "Apakah AI akan menggantikan software engineer?",
        "mode": "debate",
        "selected_providers": ["chatgpt", "claude"]
    })
    run_id = init_res.json()["id"]

    # Try advancing immediately without filling responses
    adv_res = client.post(f"/api/discussions/{run_id}/advance")
    assert adv_res.status_code == 400
    assert "Belum ada respons" in adv_res.json()["detail"]


def test_cannot_advance_stopped_discussion(client):
    """Stopping a discussion prevents further advancement."""
    init_res = client.post("/api/discussions", json={
        "query": "Evaluasi arsitektur cloud serverless.",
        "mode": "debate",
        "selected_providers": ["chatgpt"]
    })
    run_id = init_res.json()["id"]

    # Stop discussion
    stop_res = client.post(f"/api/discussions/{run_id}/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "stopped"

    # Try advancing
    adv_res = client.post(f"/api/discussions/{run_id}/advance")
    assert adv_res.status_code == 400
    assert "stopped" in adv_res.json()["detail"].lower()



def test_max_rounds_validation(client):
    """Max debate rounds is capped at 3 as mandated."""
    # Attempting to send max_rounds > 3 should be rejected by validation
    res = client.post("/api/discussions", json={
        "query": "Diskusi validasi rounds",
        "mode": "debate",
        "max_rounds": 10
    })
    assert res.status_code == 422  # Pydantic validation error


def test_cannot_submit_response_to_stopped_run(client):
    """Cannot mutate or add responses to a stopped debate session."""
    init_res = client.post("/api/discussions", json={
        "query": "[TEST] Uji mutasi sesi stopped",
        "mode": "debate",
        "selected_providers": ["chatgpt"]
    })
    run_data = init_res.json()
    run_id = run_data["id"]
    resp_id = run_data["responses"][0]["id"]

    # Stop run
    client.post(f"/api/discussions/{run_id}/stop")

    # Attempt manual response submission
    sub_res = client.post(f"/api/discussions/{run_id}/responses", json={
        "response_id": resp_id,
        "content": "[TEST DATA] Jawaban sementara",
        "status": "completed"
    })
    assert sub_res.status_code == 400
    assert "dihentikan" in sub_res.json()["detail"].lower()


def test_resume_stopped_discussion_and_continue(client):
    """Resuming a stopped run restores awaiting_input state and allows continuing."""
    init_res = client.post("/api/discussions", json={
        "query": "[TEST] Uji mekanisme resume diskusi",
        "mode": "debate",
        "selected_providers": ["chatgpt", "claude"]
    })
    run_data = init_res.json()
    run_id = run_data["id"]
    resp_id = run_data["responses"][0]["id"]

    # 1. Stop run
    stop_res = client.post(f"/api/discussions/{run_id}/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "stopped"

    # 2. Resume run
    resume_res = client.post(f"/api/discussions/{run_id}/resume")
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "awaiting_input"

    # 3. Now submit response succeeds
    sub_res = client.post(f"/api/discussions/{run_id}/responses", json={
        "response_id": resp_id,
        "content": "[TEST DATA] Analisis resume berhasil",
        "status": "completed"
    })
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "completed"


def test_cannot_create_synthesis_on_empty_run(client):
    """Cannot create moderator synthesis if 0 debater responses exist."""
    init_res = client.post("/api/discussions", json={
        "query": "[TEST] Uji pembuatan sintesis tanpa respons",
        "mode": "debate",
        "selected_providers": ["chatgpt"]
    })
    run_id = init_res.json()["id"]

    synth_res = client.post(f"/api/discussions/{run_id}/synthesis", json={
        "run_id": run_id,
        "raw_synthesis": "[TEST] Sintesis fiktif tanpa masukan peserta",
        "allow_partial": True
    })
    assert synth_res.status_code == 400
    assert "belum ada respons peserta dewan" in synth_res.json()["detail"].lower()


def test_partial_synthesis_on_stopped_run(client):
    """Partial synthesis is permitted when explicitly opted in on a run with existing responses."""
    init_res = client.post("/api/discussions", json={
        "query": "[TEST] Evaluasi parsial debate",
        "mode": "debate",
        "selected_providers": ["chatgpt", "claude"]
    })
    run_data = init_res.json()
    run_id = run_data["id"]
    resp1_id = run_data["responses"][0]["id"]

    # Submit 1 response
    client.post(f"/api/discussions/{run_id}/responses", json={
        "response_id": resp1_id,
        "content": "[TEST DATA] Analisis awal satu peserta",
        "status": "completed"
    })

    # Stop run
    client.post(f"/api/discussions/{run_id}/stop")

    # Submitting without allow_partial should fail
    fail_synth = client.post(f"/api/discussions/{run_id}/synthesis", json={
        "run_id": run_id,
        "raw_synthesis": "Sintesis tanpa izin parsial",
        "allow_partial": False
    })
    assert fail_synth.status_code == 400

    # Submitting with allow_partial=True succeeds
    ok_synth = client.post(f"/api/discussions/{run_id}/synthesis", json={
        "run_id": run_id,
        "raw_synthesis": "## Ringkasan Masalah\nAnalisis parsial selesai.",
        "allow_partial": True
    })
    assert ok_synth.status_code == 200
    assert ok_synth.json()["success"] is True

    # Verify run completed
    run_check = client.get(f"/api/discussions/{run_id}").json()
    assert run_check["status"] == "completed"


def test_export_stopped_incomplete_run_never_fabricates(client):
    """Export of stopped run must accurately document stopped state and never fabricate responses."""
    init_res = client.post("/api/discussions", json={
        "query": "[TEST] Diskusi dihentikan tanpa jawaban",
        "mode": "debate",
        "selected_providers": ["chatgpt", "claude", "gemini"]
    })
    run_id = init_res.json()["id"]

    # Stop run immediately
    client.post(f"/api/discussions/{run_id}/stop")

    export_res = client.get(f"/api/discussions/{run_id}/export")
    assert export_res.status_code == 200
    report_text = export_res.text

    # Verify header documents stopped state
    assert "STOPPED" in report_text
    assert "Dihentikan Lebih Awal" in report_text

    # Verify debater section notes no responses completed
    assert "Belum ada respons peserta dewan yang diselesaikan" in report_text

    # Verify NO moderator row is printed as a participant in Section 1
    assert "MODERATOR (final_synthesis" not in report_text

    # Verify synthesis section notes it was not generated
    assert "Sintesis belum dibuat karena sesi ini dihentikan lebih awal" in report_text

