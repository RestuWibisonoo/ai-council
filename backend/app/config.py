from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional

# Base directory for the repository
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    app_name: str = "AI Council"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    
    # Database
    database_url: str = f"sqlite:///{DATA_DIR}/ai_council.db"
    
    # Paths
    base_dir: Path = BASE_DIR
    data_dir: Path = DATA_DIR
    upload_dir: Path = UPLOAD_DIR
    
    # Limits & Security (Max 3 debate rounds strictly enforced)
    max_upload_size_bytes: int = 25 * 1024 * 1024  # 25 MB
    allowed_file_extensions: list[str] = [".pdf", ".txt", ".md"]
    max_debate_rounds: int = 3
    default_debate_rounds: int = 2
    api_timeout_seconds: float = 60.0

    @field_validator("max_debate_rounds")
    @classmethod
    def validate_max_debate_rounds(cls, v: int) -> int:
        if v > 3:
            raise ValueError(f"MAX_DEBATE_ROUNDS={v} melebihi batas maksimal 3 putaran yang diizinkan.")
        if v < 1:
            raise ValueError(f"MAX_DEBATE_ROUNDS={v} minimal 1 putaran.")
        return v

    @field_validator("default_debate_rounds")
    @classmethod
    def validate_default_debate_rounds(cls, v: int) -> int:
        if v > 3:
            raise ValueError(f"DEFAULT_DEBATE_ROUNDS={v} tidak boleh melebihi batas 3 putaran.")
        if v < 1:
            return 1
        return v

    # API Keys & Providers (optional; read from environment or updated via encrypted/local settings)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    dashscope_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"

    # Zero-Cost Mode & Safety Limits
    zero_cost_mode: bool = True
    ai_council_zero_cost_mode: bool = True
    max_requests_per_run: int = 30
    max_tokens_per_response: int = 2048

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )



settings = Settings()
