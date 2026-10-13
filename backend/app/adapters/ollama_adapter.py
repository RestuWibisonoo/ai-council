from typing import Optional, List, Dict, Any, Tuple
import httpx
from app.adapters.base import BaseAIAdapter, AdapterResult
from app.config import settings


class OllamaAdapter(BaseAIAdapter):
    DEFAULT_MODEL = "llama3.2"

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        super().__init__(api_key=None, model=model)
        self.base_url = (base_url or settings.ollama_base_url or "http://localhost:11434").rstrip("/")

    @classmethod
    async def is_available(cls, base_url: Optional[str] = None) -> bool:
        """Check if local Ollama daemon is reachable."""
        url = (base_url or settings.ollama_base_url or "http://localhost:11434").rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    @classmethod
    async def get_installed_models(cls, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch list of locally installed models from Ollama."""
        url = (base_url or settings.ollama_base_url or "http://localhost:11434").rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(f"{url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = []
                    for m in data.get("models", []):
                        models.append({
                            "id": m.get("name"),
                            "name": f"{m.get('name')} (Lokal)",
                            "size_bytes": m.get("size", 0),
                            "modified_at": m.get("modified_at", ""),
                            "is_free": True,
                            "provider": "ollama"
                        })
                    return models
        except Exception:
            pass
        return []

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: float = 120.0
    ) -> AdapterResult:
        model_name = self.model or self.DEFAULT_MODEL

        # Check daemon availability
        if not await self.is_available(self.base_url):
            return AdapterResult(
                content="",
                model_id=model_name,
                error=(
                    f"Ollama lokal tidak aktif pada {self.base_url}. "
                    "Pastikan aplikasi Ollama berjalan di Mac Anda ('ollama serve') atau pilih model cloud."
                )
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Ollama supports OpenAI-compatible /v1/chat/completions
        chat_url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(chat_url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        return AdapterResult(
                            content="",
                            model_id=model_name,
                            error="Ollama mengembalikan respons kosong."
                        )

                    content = choices[0].get("message", {}).get("content", "")
                    usage = data.get("usage", {})
                    p_tokens = usage.get("prompt_tokens", 0)
                    c_tokens = usage.get("completion_tokens", 0)
                    t_tokens = usage.get("total_tokens", p_tokens + c_tokens)

                    return AdapterResult(
                        content=content,
                        prompt_tokens=p_tokens,
                        completion_tokens=c_tokens,
                        total_tokens=t_tokens,
                        estimated_cost_usd=0.0,
                        model_id=model_name,
                        is_actual_cost=True
                    )
                elif resp.status_code == 404:
                    return AdapterResult(
                        content="",
                        model_id=model_name,
                        error=(
                            f"Model Ollama '{model_name}' belum diunduh di Mac Anda. "
                            f"Jalankan 'ollama pull {model_name}' di Terminal untuk mengunduh model ini."
                        )
                    )
                else:
                    return AdapterResult(
                        content="",
                        model_id=model_name,
                        error=f"Ollama mengembalikan status HTTP {resp.status_code}: {resp.text}"
                    )
        except httpx.TimeoutException:
            return AdapterResult(
                content="",
                model_id=model_name,
                error=f"Ollama timeout setelah {timeout} detik saat mengeksekusi '{model_name}'."
            )
        except Exception as e:
            return AdapterResult(
                content="",
                model_id=model_name,
                error=f"Gagal menghubungi server Ollama: {str(e)}"
            )

    async def test_connection(self) -> Tuple[bool, str]:
        available = await self.is_available(self.base_url)
        if not available:
            return False, f"Ollama tidak merespons di {self.base_url}. Pastikan daemon Ollama aktif."

        models = await self.get_installed_models(self.base_url)
        if not models:
            return True, f"Ollama terhubung di {self.base_url}, namun belum ada model yang terpasang. Jalankan 'ollama pull <nama-model>'."
        model_names = ", ".join(m["id"] for m in models[:3])
        return True, f"Ollama aktif ({len(models)} model terpasang: {model_names})."
