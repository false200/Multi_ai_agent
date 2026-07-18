from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    tavily_api_key: str | None = field(default_factory=lambda: os.getenv("TAVILY_API_KEY"))
    backend_host: str = field(default_factory=lambda: os.getenv("BACKEND_HOST", "127.0.0.1"))
    backend_port: int = field(
        default_factory=lambda: int(os.getenv("BACKEND_PORT", "9999"))
    )
    api_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("API_TIMEOUT_SECONDS", "120"))
    )
    allowed_model_names: tuple[str, ...] = (
        "llama3-70b-8192",
        "llama-3.3-70b-versatile",
    )
    tavily_max_results: int = 2

    @property
    def chat_api_url(self) -> str:
        return f"http://{self.backend_host}:{self.backend_port}/chat"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
