"""Uygulama ayarları için tek kaynak."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """V1 için dış bağımlılık gerektirmeyen güvenli varsayılanlar."""

    max_upload_bytes: int = 5 * 1024 * 1024
    application_name: str = "FaturaGuard AI"
    application_version: str = "0.1.0"
    data_directory: Path = Path("data")
    # Dört gerçek bulgu vakasındaki benchmark'ta %100 geçerli yapılandırılmış çıktı
    # üreten Gemma 3 4B varsayılandır. Gerekirse OLLAMA_MODEL ile değiştirilebilir.
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    # auto: GEMINI_API_KEY tanımlıysa hızlı API, değilse tamamen yerel Ollama kullanılır.
    llm_provider: str = os.getenv("LLM_PROVIDER", "auto").lower()
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    n8n_webhook_url: str | None = os.getenv("N8N_WEBHOOK_URL") or None


settings = Settings()
