"""Belgeye bağlı, yerelde saklanan sohbet kayıtları."""

from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, computed_field, field_validator


class ChatCitation(BaseModel):
    source_title: str
    source_url: str
    page: int = Field(ge=1)
    excerpt: str = Field(default="", max_length=600)

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
    providers: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    masked_conversation_sent: bool = False
    failure_code: str | None = None
    validation_issues: list[str] = Field(default_factory=list)
    repair_attempted: bool = False
    generated_by: Literal["gemini", "groq", "local", "unknown"] = "unknown"
    basis_recorded: bool = False
    basis_findings: list[str] = Field(default_factory=list)
    basis_records: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @computed_field
    @property
    def producer_label(self) -> str:
        if self.generated_by == "local" or self.mode in {
            "local_fallback", "overview", "comparison", "proposal", "guidance",
            "clarification", "safety_boundary", "unavailable", "source_summary",
        }:
            return "Yerel kayıt özeti"
        if self.generated_by in {"gemini", "groq"}:
            return f"{self.generated_by.title()} tarafından üretildi"
        return "AI tarafından üretildi · Sağlayıcı kaydı yok"
