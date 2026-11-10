"""RAG katmanının kullanabileceği resmî kaynak envanteri."""

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse


class SourcePolicyError(ValueError):
    """Bir kaynak GİB kaynak politikasına uymadığında yükseltilir."""


@dataclass(frozen=True, slots=True)
class OfficialSource:
    source_id: str
    title: str
    url: str
    status: str
    local_file: str | None = None
    expected_sha256: str | None = None


class OfficialSourceCatalog:
    """Sadece GİB tarafından yayımlanan, envantere alınmış kaynakları açar."""

    def __init__(self, catalog_path: Path) -> None:
        self._catalog_path = catalog_path
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        self._allowed_domains = frozenset(payload["policy"]["allowed_domains"])
        self._sources = tuple(self._parse_source(item) for item in payload["sources"])

    @property
    def sources(self) -> tuple[OfficialSource, ...]:
        return self._sources

    def verified_local_sources(self) -> tuple[OfficialSource, ...]:
        """Yerel kopyası mevcut ve kaydedilmiş SHA-256 özetiyle eşleşen kaynakları döndürür."""
        verified: list[OfficialSource] = []
        for source in self._sources:
            if not source.local_file or not source.expected_sha256:
                continue
            path = self._catalog_path.parent / source.local_file
            if path.is_file() and self._sha256(path) == source.expected_sha256.lower():
                verified.append(source)
        return tuple(verified)

    def local_path(self, source: OfficialSource) -> Path:
        """Envantere ait bir kaynağın yerel kopya yolunu döndürür."""
        if source not in self._sources or not source.local_file:
            raise SourcePolicyError(
                "Envanterde olmayan veya yerel kopyası bulunmayan kaynak istendi."
            )
        return self._catalog_path.parent / source.local_file

    def _parse_source(self, item: dict[str, object]) -> OfficialSource:
        url = str(item["url"])
        hostname = urlparse(url).hostname
        if hostname not in self._allowed_domains:
            raise SourcePolicyError(f"İzin verilmeyen RAG kaynağı: {url}")
        return OfficialSource(
            source_id=str(item["id"]),
            title=str(item["title"]),
            url=url,
            status=str(item["status"]),
            local_file=str(item["local_file"]) if item.get("local_file") else None,
            expected_sha256=str(item["sha256"]).lower() if item.get("sha256") else None,
        )

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(64 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
