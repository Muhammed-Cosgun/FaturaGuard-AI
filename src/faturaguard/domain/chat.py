"""Belgeye bağlı, yerelde saklanan sohbet kayıtları."""

from datetime import UTC, datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class ChatCitation(BaseModel):
    source_title: str
    source_url: str
    page: int = Field(ge=1)

    @field_validator("source_url")
    @classmethod
    def official_url(cls, value: str) -> str:
        url = urlparse(value)
        if (
            url.scheme != "https"
            or url.hostname not in {"ebelge.gib.gov.tr", "www.gib.gov.tr"}
            or url.username
            or url.password
        ):
            raise ValueError("Sohbet atfı resmî HTTPS GİB bağlantısı olmalıdır.")
        return value


class ChatTurn(BaseModel):
    question: str = Field(min_length=1, max_length=600)
    answer: str
    mode: str
    finding_code: str | None = None
    citations: list[ChatCitation] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
