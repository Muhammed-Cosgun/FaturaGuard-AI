"""Resmî GİB dokümanlarından kaynaklı, yerel arama katmanı."""

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from faturaguard.services.official_source_catalog import OfficialSource, OfficialSourceCatalog

TOKEN_PATTERN = re.compile(r"[a-zçğıöşü0-9]{2,}", re.IGNORECASE)


class TextExtractor(Protocol):
    def extract_pages(self, path: Path) -> list[str]: ...


class PdfTextExtractor:
    """PDF metin çıkarımını isteğe bağlı pypdf bağımlılığıyla yapar."""

    def extract_pages(self, path: Path) -> list[str]:
        try:
            from pypdf import PdfReader
        except ImportError as error:
            raise RuntimeError("RAG indeksi için pypdf bağımlılığı kurulmalıdır.") from error
        return [(page.extract_text() or "").strip() for page in PdfReader(path).pages]


@dataclass(frozen=True, slots=True)
class RagChunk:
    source_id: str
    source_title: str
    source_url: str
    page: int
    text: str


@dataclass(frozen=True, slots=True)
class RagAnswer:
    text: str
    citations: tuple[RagChunk, ...]


def _tokens(value: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(value.lower()))


class OfficialRagIndex:
    """Harici LLM çağırmadan önce kanıt parçalarını bulan, denetlenebilir arama indisi."""

    def __init__(self, chunks: list[RagChunk]) -> None:
        self._chunks = chunks

    @property
    def chunks(self) -> tuple[RagChunk, ...]:
        return tuple(self._chunks)

    def search(self, query: str, limit: int = 3) -> tuple[RagChunk, ...]:
        query_tokens = _tokens(query)
        ranked = [
            (len(query_tokens.intersection(_tokens(chunk.text))), chunk) for chunk in self._chunks
        ]
        ranked = [item for item in ranked if item[0] > 0]
        ranked.sort(key=lambda item: (item[0], -item[1].page), reverse=True)
        return tuple(chunk for _, chunk in ranked[:limit])

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps([asdict(chunk) for chunk in self._chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "OfficialRagIndex":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls([RagChunk(**item) for item in payload])


class OfficialRagIndexer:
    """Yalnızca katalogda doğrulanmış GİB PDF kaynaklarını indeksler."""

    def __init__(self, catalog: OfficialSourceCatalog, extractor: TextExtractor) -> None:
        self._catalog = catalog
        self._extractor = extractor

    def build(self) -> OfficialRagIndex:
        chunks: list[RagChunk] = []
        for source in self._catalog.verified_local_sources():
            if not source.local_file or not source.local_file.lower().endswith(".pdf"):
                continue
            source_path = self._catalog.local_path(source)
            pages = self._extractor.extract_pages(source_path)
            for page_number, page_text in enumerate(pages, start=1):
                chunks.extend(self._chunk_page(source, page_number, page_text))
        return OfficialRagIndex(chunks)

    @staticmethod
    def _chunk_page(source: OfficialSource, page: int, text: str) -> list[RagChunk]:
        clean_text = " ".join(text.split())
        if not clean_text:
            return []
        size, overlap = 900, 180
        chunks: list[RagChunk] = []
        start = 0
        while start < len(clean_text):
            end = min(len(clean_text), start + size)
            chunks.append(
                RagChunk(source.source_id, source.title, source.url, page, clean_text[start:end])
            )
            if end == len(clean_text):
                break
            start = end - overlap
        return chunks
