from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class AdapterResult(BaseModel):
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model_id: str
    is_actual_cost: bool = False
    error: Optional[str] = None


class BaseAIAdapter(ABC):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: float = 60.0
    ) -> AdapterResult:
        pass

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        pass
