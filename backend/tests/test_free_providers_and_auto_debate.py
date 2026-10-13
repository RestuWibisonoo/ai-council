import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import DiscussionRun, ModelResponse, Synthesis
from app.adapters.openrouter_adapter import OpenRouterAdapter
from app.adapters.ollama_adapter import OllamaAdapter
from app.adapters.deepseek_adapter import DeepSeekAdapter
from app.adapters.qwen_adapter import QwenAdapter
from app.services.orchestrator import Orchestrator
from app.services.provider_manager import provider_manager
from tests.conftest import TestingSessionLocal


# ---------------------------------------------------------------------------
# 1. OpenRouter Catalog & Zero-Cost Pricing Verification
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_openrouter_catalog_and_zero_cost_verification():
    adapter = OpenRouterAdapter(api_key="sk-or-test-dummy-key")

    mock_models_response = {
        "data": [
            {
                "id": "deepseek/deepseek-r1:free",
                "name": "DeepSeek: DeepSeek R1 (free)",
                "pricing": {"prompt": "0", "completion": "0"},
                "context_length": 64000
            },
            {
                "id": "meta-llama/llama-3.3-70b-instruct:free",
                "name": "Meta: Llama 3.3 70B Instruct (free)",
                "pricing": {"prompt": "0.0", "completion": "0.0"},
                "context_length": 131072
            },
            {
                "id": "openai/gpt-4o",
                "name": "OpenAI: GPT-4o",
                "pricing": {"prompt": "0.000005", "completion": "0.000015"},
                "context_length": 128000
            },
            {
                "id": "unverified/mystery-model",
                "name": "Mystery Model",
                "pricing": {},
                "context_length": 4096
            }
        ]
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_models_response
        mock_get.return_value = mock_resp

        free_models = await adapter.get_free_models()
        model_ids = [m["id"] for m in free_models]

        assert "deepseek/deepseek-r1:free" in model_ids
        assert "meta-llama/llama-3.3-70b-instruct:free" in model_ids
        assert "openai/gpt-4o" not in model_ids
        assert "unverified/mystery-model" not in model_ids

        # Price verification helper
        is_free_r1, reason1 = await adapter.verify_model_is_free("deepseek/deepseek-r1:free")
        assert is_free_r1 is True
        assert "Gratis" in reason1

        is_free_paid, reason2 = await adapter.verify_model_is_free("openai/gpt-4o")
        assert is_free_paid is False
        assert "berbayar" in reason2

        is_free_unknown, reason3 = await adapter.verify_model_is_free("nonexistent/model")
        assert is_free_unknown is False


# ---------------------------------------------------------------------------
# 2. Zero-Cost Mode Rejection of Paid Models
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_zero_cost_mode_strictly_rejects_paid_models():
    adapter = OpenRouterAdapter(api_key="sk-or-test-key", model="openai/gpt-4o", zero_cost_mode=True)

    with patch.object(adapter, "verify_model_is_free", AsyncMock(return_value=(False, "Model berbayar"))):
        result = await adapter.complete(prompt="Jelaskan fisika kuantum.")
        assert result.content == ""
        assert result.error is not None
        assert "Keamanan Biaya (Zero-Cost Mode)" in result.error

    # DeepSeek Direct API rejects in Zero-Cost Mode
    ds_adapter = DeepSeekAdapter(api_key="ds-secret-key", zero_cost_mode=True)
    ds_res = await ds_adapter.complete(prompt="Halo DeepSeek")
    assert ds_res.content == ""
    assert ds_res.error is not None
    assert "Keamanan Biaya (Zero-Cost Mode)" in ds_res.error


# ---------------------------------------------------------------------------
# 3. OpenRouter API Key Leaking & Error Sanitization (401, 429, Timeout)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_openrouter_error_handling_and_key_sanitization():
    secret_key = "sk-or-v1-secret-token-999"
    adapter = OpenRouterAdapter(api_key=secret_key, model="deepseek/deepseek-r1:free", zero_cost_mode=False)

    # Test 401 Authentication Error
    with patch("httpx.AsyncClient.post") as mock_post:
        resp_401 = MagicMock()
        resp_401.status_code = 401
        resp_401.text = f"Invalid token {secret_key}"
        mock_post.return_value = resp_401

        res_401 = await adapter.complete(prompt="Test")
        assert res_401.error is not None
        assert secret_key not in res_401.error
        assert "Autentikasi Gagal" in res_401.error or "HTTP 401" in res_401.error

    # Test Timeout
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Connection timed out")):
        res_to = await adapter.complete(prompt="Test")
        assert res_to.error is not None
        assert "timeout" in res_to.error.lower()


# ---------------------------------------------------------------------------
# 4. OpenRouter 429 Rate Limit Retry & Backoff
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_openrouter_429_rate_limit_retry():
    adapter = OpenRouterAdapter(api_key="sk-or-test-key", model="deepseek/deepseek-r1:free", zero_cost_mode=False)

    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.text = "Rate limit exceeded"

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "choices": [{"message": {"content": "Jawaban berhasil setelah retry!"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
    }

    # First call 429, second call 200 (recovers with backoff)
    with patch("httpx.AsyncClient.post", side_effect=[resp_429, resp_200]), \
         patch("asyncio.sleep", AsyncMock()):
        res = await adapter.complete(prompt="Uji retry")
        assert res.error is None
        assert "Jawaban berhasil" in res.content


# ---------------------------------------------------------------------------
# 5. Ollama Local Model & Offline Isolation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ollama_offline_isolation_and_model_detection():
    ollama = OllamaAdapter(base_url="http://127.0.0.1:11434")

    # When Ollama daemon is offline:
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
        is_up = await ollama.is_available("http://127.0.0.1:11434")
        assert is_up is False

        # Attempting to query when offline returns clear error without crashing
        res = await ollama.complete(prompt="Halo")
        assert res.error is not None
        assert "tidak aktif" in res.error

    # When Ollama daemon is online:
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [
                {"name": "llama3.2:latest", "size": 2000000000},
                {"name": "qwen2.5:7b", "size": 4000000000}
            ]
        }
        mock_get.return_value = mock_resp

        models = await ollama.get_installed_models("http://127.0.0.1:11434")
        model_names = [m["id"] for m in models]
        assert "llama3.2:latest" in model_names
        assert "qwen2.5:7b" in model_names


# ---------------------------------------------------------------------------
# 6. Catalog Endpoint in Providers Router
# ---------------------------------------------------------------------------
def test_providers_catalog_models_endpoint(client: TestClient):
    mock_free_catalog = [
        {"id": "deepseek/deepseek-r1:free", "name": "DeepSeek R1", "family": "DeepSeek", "is_free": True},
        {"id": "qwen/qwen-2.5-72b:free", "name": "Qwen 2.5 72B", "family": "Qwen", "is_free": True},
        {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3", "family": "Meta Llama", "is_free": True}
    ]

    with patch("app.adapters.openrouter_adapter.OpenRouterAdapter.get_free_models", AsyncMock(return_value=mock_free_catalog)):
        resp = client.get("/api/providers/catalog/models")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        families = {m.get("family") for m in data}
        assert "DeepSeek" in families or any("deepseek" in m.get("id", "") for m in data)


class SessionWrapper:
    def __init__(self, s):
        self.s = s
    def __enter__(self):
        return self.s
    def __exit__(self, *args):
        pass
    def __getattr__(self, name):
        return getattr(self.s, name)


# ---------------------------------------------------------------------------
# 7. Automated Debate State Machine (Full Auto 1-Click Run)
# ---------------------------------------------------------------------------
def test_automated_debate_flow_to_final_synthesis(client: TestClient, db_session: Session):
    create_resp = client.post("/api/discussions", json={
        "mode": "debate",
        "query": "Apakah AI open-weight akan melampaui AI proprietary?",
        "selected_providers": ["openrouter:deepseek/deepseek-r1:free", "openrouter:qwen/qwen-2.5-72b:free"],
        "max_rounds": 1,
        "auto_run": False
    })
    assert create_resp.status_code == 201
    run_id = create_resp.json()["id"]

    # Mock completions for debaters and moderator
    async def mock_execute_api_tasks(*args, **kwargs):
        tasks = kwargs.get("tasks") or (args[1] if len(args) > 1 else args[0])
        for resp_id, prov, mid, prompt in tasks:
            r = db_session.query(ModelResponse).filter_by(id=resp_id).first()
            if r:
                r.status = "completed"
                r.content = f"Argumen matang dari model {mid} pada tahap {r.stage}."
        db_session.commit()

    async def mock_execute_synth(*args, **kwargs):
        target_run_id = kwargs.get("run_id") or (args[1] if len(args) > 1 else args[0])
        synth = Synthesis(
            run_id=target_run_id,
            moderator_provider="openrouter:deepseek/deepseek-r1:free",
            mode="api",
            problem_summary="Konsensus lengkap dewan AI: Kedua model menyepakati akselerasi open-weight.",
            consensus_points="Open-weight berkembang pesat",
            disagreements="Tenggat waktu melampaui",
            raw_synthesis="Ringkasan konsensus antar model."
        )
        db_session.add(synth)
        run_obj = db_session.query(DiscussionRun).filter(DiscussionRun.id == target_run_id).first()
        if run_obj:
            run_obj.status = "completed"
            run_obj.current_stage = "completed"
        db_session.commit()

    with patch.object(Orchestrator, "get_db_session", staticmethod(lambda: SessionWrapper(db_session))), \
         patch.object(Orchestrator, "_execute_api_tasks_concurrent", staticmethod(mock_execute_api_tasks)), \
         patch.object(Orchestrator, "_execute_automated_synthesis", staticmethod(mock_execute_synth)):

        asyncio.run(
            Orchestrator.run_automated_debate(
                run_id=run_id,
                moderator_model="openrouter:deepseek/deepseek-r1:free",
                zero_cost_mode=True
            )
        )

    # Verify run completed through to final synthesis
    db_session.expire_all()
    finished_run = db_session.query(DiscussionRun).filter(DiscussionRun.id == run_id).first()
    assert finished_run.status == "completed"
    assert finished_run.current_stage == "completed"

    syntheses = db_session.query(Synthesis).filter(Synthesis.run_id == run_id).all()
    assert len(syntheses) == 1
    assert "Konsensus lengkap" in (syntheses[0].problem_summary or "")


# ---------------------------------------------------------------------------
# 8. Partial Failure Containment in Automated Debate
# ---------------------------------------------------------------------------
def test_automated_debate_partial_failure_containment(client: TestClient, db_session: Session):
    create_resp = client.post("/api/discussions", json={
        "mode": "debate",
        "query": "Manfaat teknologi kuantum untuk kriptografi?",
        "selected_providers": ["openrouter:model-success:free", "openrouter:model-fail:free"],
        "max_rounds": 1,
        "auto_run": False
    })
    assert create_resp.status_code == 201
    run_id = create_resp.json()["id"]

    async def mock_execute_api_tasks_with_failure(*args, **kwargs):
        tasks = kwargs.get("tasks") or (args[1] if len(args) > 1 else args[0])
        for resp_id, prov, mid, prompt in tasks:
            r = db_session.query(ModelResponse).filter_by(id=resp_id).first()
            if r:
                if "fail" in (mid or ""):
                    r.status = "failed"
                    r.error_message = "Rate limit HTTP 429: Kuota sementara penuh"
                else:
                    r.status = "completed"
                    r.content = f"Analisis berhasil dari {mid}"
        db_session.commit()

    async def mock_execute_synth_partial(*args, **kwargs):
        target_run_id = kwargs.get("run_id") or (args[1] if len(args) > 1 else args[0])
        synth = Synthesis(
            run_id=target_run_id,
            moderator_provider="openrouter:model-success:free",
            mode="api",
            problem_summary="Sintesis parsial atas respons yang berhasil.",
            raw_synthesis="Ringkasan sintesis parsial."
        )
        db_session.add(synth)
        run_obj = db_session.query(DiscussionRun).filter(DiscussionRun.id == target_run_id).first()
        if run_obj:
            run_obj.status = "completed"
            run_obj.current_stage = "completed"
        db_session.commit()

    with patch.object(Orchestrator, "get_db_session", staticmethod(lambda: SessionWrapper(db_session))), \
         patch.object(Orchestrator, "_execute_api_tasks_concurrent", staticmethod(mock_execute_api_tasks_with_failure)), \
         patch.object(Orchestrator, "_execute_automated_synthesis", staticmethod(mock_execute_synth_partial)):

        asyncio.run(
            Orchestrator.run_automated_debate(
                run_id=run_id,
                moderator_model="openrouter:model-success:free",
                zero_cost_mode=True
            )
        )

    db_session.expire_all()
    failed_resp = db_session.query(ModelResponse).filter(
        ModelResponse.run_id == run_id,
        ModelResponse.status == "failed"
    ).first()
    assert failed_resp is not None
    assert "Rate limit HTTP 429" in failed_resp.error_message

    success_resp = db_session.query(ModelResponse).filter(
        ModelResponse.run_id == run_id,
        ModelResponse.status == "completed"
    ).first()
    assert success_resp is not None
    assert "Analisis berhasil" in success_resp.content


# ---------------------------------------------------------------------------
# 9. All Participants Fail Aborts Gracefully
# ---------------------------------------------------------------------------
def test_automated_debate_all_fail_aborts(client: TestClient, db_session: Session):
    create_resp = client.post("/api/discussions", json={
        "mode": "debate",
        "query": "Pertanyaan uji kegagalan total",
        "selected_providers": ["openrouter:model-fail-1:free", "openrouter:model-fail-2:free"],
        "max_rounds": 1,
        "auto_run": False
    })
    assert create_resp.status_code == 201
    run_id = create_resp.json()["id"]

    async def mock_execute_all_fail(*args, **kwargs):
        tasks = kwargs.get("tasks") or (args[1] if len(args) > 1 else args[0])
        for resp_id, prov, mid, prompt in tasks:
            r = db_session.query(ModelResponse).filter_by(id=resp_id).first()
            if r:
                r.status = "failed"
                r.error_message = "API provider tidak dapat dihubungi (HTTP 503)"
        db_session.commit()

    with patch.object(Orchestrator, "get_db_session", staticmethod(lambda: SessionWrapper(db_session))), \
         patch.object(Orchestrator, "_execute_api_tasks_concurrent", staticmethod(mock_execute_all_fail)):
        asyncio.run(
            Orchestrator.run_automated_debate(
                run_id=run_id,
                zero_cost_mode=True
            )
        )

    db_session.expire_all()
    failed_run = db_session.query(DiscussionRun).filter(DiscussionRun.id == run_id).first()
    assert failed_run.status == "failed"

    # Synthesis should NOT have been produced
    syntheses = db_session.query(Synthesis).filter(Synthesis.run_id == run_id).all()
    assert len(syntheses) == 0


# ---------------------------------------------------------------------------
# 10. Stop and Resume Discussion Run
# ---------------------------------------------------------------------------
def test_stop_and_resume_discussion(client: TestClient):
    create_resp = client.post("/api/discussions", json={
        "mode": "debate",
        "query": "Uji fitur Stop dan Resume",
        "selected_providers": ["chatgpt", "claude"],
        "max_rounds": 1,
        "auto_run": False
    })
    assert create_resp.status_code == 201
    run_id = create_resp.json()["id"]

    # Stop discussion
    stop_resp = client.post(f"/api/discussions/{run_id}/stop")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["status"] == "stopped"

    # Resume discussion
    resume_resp = client.post(f"/api/discussions/{run_id}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "awaiting_input"


# ---------------------------------------------------------------------------
# 11. Report Export (Markdown and TXT) with Free Providers
# ---------------------------------------------------------------------------
def test_export_report_markdown_and_txt_with_free_models(client: TestClient, db_session: Session):
    create_resp = client.post("/api/discussions", json={
        "mode": "debate",
        "query": "Perbandingan arsitektur Transformer dan SSM (Mamba)",
        "selected_providers": ["openrouter:deepseek/deepseek-r1:free", "openrouter:qwen/qwen-2.5-72b:free"],
        "max_rounds": 1,
        "auto_run": False
    })
    assert create_resp.status_code == 201
    run_id = create_resp.json()["id"]

    # Complete initial responses
    run_data = create_resp.json()
    for resp in run_data["responses"]:
        client.post(f"/api/discussions/{run_id}/responses", json={
            "response_id": resp["id"],
            "content": f"Analisis teknis dari model {resp['model_id']}.",
            "status": "completed"
        })

    # Test Markdown export
    md_resp = client.get(f"/api/discussions/{run_id}/export?format=md")
    assert md_resp.status_code == 200
    assert "Perbandingan arsitektur Transformer" in md_resp.text
    assert "deepseek" in md_resp.text.lower()

    # Test TXT export
    txt_resp = client.get(f"/api/discussions/{run_id}/export?format=txt")
    assert txt_resp.status_code == 200
    assert "Perbandingan arsitektur Transformer" in txt_resp.text


# ---------------------------------------------------------------------------
# 12. Auto Debate Endpoint: Idempotency and NameError Prevention
# ---------------------------------------------------------------------------
def test_auto_debate_endpoint_idempotency_and_no_name_error(client: TestClient, db_session: Session):
    create_resp = client.post("/api/discussions", json={
        "mode": "debate",
        "query": "Uji endpoint auto debate",
        "selected_providers": ["openrouter:deepseek/deepseek-r1:free"],
        "max_rounds": 1,
        "auto_run": False
    })
    assert create_resp.status_code == 201
    run_id = create_resp.json()["id"]

    with patch.object(Orchestrator, "run_automated_debate", AsyncMock()):
        # First call: triggers debate
        resp1 = client.post(f"/api/discussions/{run_id}/run-auto")
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "in_progress"

        # Second call (double-click): idempotent, does not crash or spawn second task
        resp2 = client.post(f"/api/discussions/{run_id}/run-auto")
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "in_progress"


# ---------------------------------------------------------------------------
# 13. Strict Zero-Cost Mode: Rejects Missing Catalog & Fake Free Models
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_strict_zero_cost_mode_rejects_missing_catalog_and_fake_free():
    adapter = OpenRouterAdapter(api_key="sk-or-test-key", zero_cost_mode=True)
    OpenRouterAdapter._models_cache = None

    # When catalog network request fails:
    with patch("httpx.AsyncClient.get", side_effect=Exception("Network failure")):
        is_free, reason = await adapter.verify_model_is_free("deepseek/deepseek-r1:free")
        assert is_free is False
        assert "tidak dapat dimuat" in reason

    # When model has :free suffix but is NOT in official catalog:
    mock_catalog = [
        {"id": "official/free-model", "pricing": {"prompt": "0", "completion": "0"}}
    ]
    with patch.object(OpenRouterAdapter, "get_models_catalog", AsyncMock(return_value=mock_catalog)):
        is_free, reason = await adapter.verify_model_is_free("fabricated/model:free")
        assert is_free is False
        assert "tidak ditemukan" in reason

    # Qwen direct adapter rejected in Zero-Cost Mode
    qwen = QwenAdapter(api_key="qwen-key", zero_cost_mode=True)
    res = await qwen.complete(prompt="Halo Qwen")
    assert res.content == ""
    assert "Keamanan Biaya (Zero-Cost Mode)" in res.error


# ---------------------------------------------------------------------------
# 14. Moderator Selection in Zero-Cost Mode: No Paid Fallback
# ---------------------------------------------------------------------------
def test_moderator_selection_zero_cost_rejection_without_paid_fallback(client: TestClient, db_session: Session):
    create_resp = client.post("/api/discussions", json={
        "mode": "debate",
        "query": "Uji moderator Zero-Cost Mode",
        "selected_providers": ["openrouter:deepseek/deepseek-r1:free"],
        "max_rounds": 1,
        "auto_run": False
    })
    run_id = create_resp.json()["id"]

    # Set up final synthesis response
    synth_resp = ModelResponse(
        run_id=run_id,
        round_id="dummy-round",
        provider="moderator",
        model_id="unknown",
        stage="final_synthesis",
        integration_mode="api",
        prompt_used="Rangkum sintesis dewan",
        content="",
        status="pending"
    )
    db_session.add(synth_resp)
    db_session.commit()

    # Simulate environment where NO free moderator is available and NO participants succeeded
    with patch.object(Orchestrator, "get_db_session", staticmethod(lambda: SessionWrapper(db_session))), \
         patch("app.services.provider_manager.provider_manager.get_secret", return_value=None), \
         patch("app.services.provider_manager.provider_manager.get_adapter", return_value=None):

        asyncio.run(
            Orchestrator._execute_automated_synthesis(
                run_id=run_id,
                moderator_model=None,
                zero_cost_mode=True
            )
        )

    db_session.expire_all()
    updated_synth = db_session.query(ModelResponse).filter_by(run_id=run_id, stage="final_synthesis").first()
    assert updated_synth.status == "failed"
    assert "Zero-Cost Mode" in updated_synth.error_message

    # Ensure no fake synthesis was inserted
    syntheses = db_session.query(Synthesis).filter_by(run_id=run_id).all()
    assert len(syntheses) == 0

