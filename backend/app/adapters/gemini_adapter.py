from typing import Optional
import httpx
from app.adapters.base import BaseAIAdapter, AdapterResult


class GeminiAdapter(BaseAIAdapter):
    DEFAULT_MODEL = "gemini-2.5-flash"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    PRICING = {
        "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    }

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: float = 60.0
    ) -> AdapterResult:
        if not self.api_key:
            return AdapterResult(
                content="",
                model_id=self.model or self.DEFAULT_MODEL,
                error="Google Gemini API key belum dikonfigurasi. Silakan atur API key di Pengaturan Provider atau gunakan Mode Manual Bridge."
            )

        model_name = self.model or self.DEFAULT_MODEL
        url = f"{self.BASE_URL}/{model_name}:generateContent?key={self.api_key}"

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System Directive: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow your directives."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {"temperature": 0.7}
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    err_json = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    msg = err_json.get("error", {}).get("message", resp.text)
                    return AdapterResult(
                        content="",
                        model_id=model_name,
                        error=f"Gemini API Error ({resp.status_code}): {msg}"
                    )

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return AdapterResult(
                        content="",
                        model_id=model_name,
                        error="Gemini tidak mengembalikan kandidat respons."
                    )

                parts = candidates[0].get("content", {}).get("parts", [])
                text_content = "".join([p.get("text", "") for p in parts])

                usage_meta = data.get("usageMetadata", {})
                p_tokens = usage_meta.get("promptTokenCount", 0)
                c_tokens = usage_meta.get("candidatesTokenCount", 0)
                t_tokens = usage_meta.get("totalTokenCount", p_tokens + c_tokens)

                rates = self.PRICING.get(model_name, {"input": 0.075, "output": 0.30})
                cost = (p_tokens * rates["input"] + c_tokens * rates["output"]) / 1_000_000.0

                return AdapterResult(
                    content=text_content,
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=t_tokens,
                    estimated_cost_usd=round(cost, 6),
                    model_id=model_name,
                    is_actual_cost=False
                )
        except Exception as e:
            return AdapterResult(
                content="",
                model_id=model_name,
                error=f"Koneksi ke Gemini API gagal: {str(e)}"
            )

    async def test_connection(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "API key Gemini belum diisi."
        try:
            url = f"{self.BASE_URL}/gemini-1.5-flash:generateContent?key={self.api_key}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": "ping"}]}]
                    }
                )
                if resp.status_code == 200:
                    return True, "Koneksi ke Google Gemini API berhasil."
                return False, f"Gemini mengembalikan kode {resp.status_code}"
        except Exception as e:
            return False, f"Gagal menghubungi server Google Gemini: {str(e)}"
