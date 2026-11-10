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
    # 3B instruct model, CPU üzerinde sunum için kabul edilebilir yanıt süresi sağlar.
    # Daha güçlü model istenirse OLLAMA_MODEL=qwen2.5:7b ile geçersiz kılınabilir.
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    n8n_webhook_url: str | None = os.getenv("N8N_WEBHOOK_URL") or None


settings = Settings()
