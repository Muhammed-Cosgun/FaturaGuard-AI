"""Orijinal XML belgelerinin değiştirilemez işlem kopyalarını saklar."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4


class FilePolicyError(ValueError):
    """Yüklenen dosya güvenlik veya ürün politikasını ihlal ettiğinde yükseltilir."""


@dataclass(frozen=True, slots=True)
class StoredDocument:
    job_id: str
    original_filename: str
    path: Path
    sha256: str
    size_bytes: int


class DocumentStorage:
    """Kullanıcının yüklediği orijinal belgeyi hiçbir zaman değiştirmez."""

    def __init__(self, root: Path, max_upload_bytes: int) -> None:
        self._originals_root = root / "originals"
        self._max_upload_bytes = max_upload_bytes

    def store_original(self, contents: bytes, upload_filename: str) -> StoredDocument:
        filename = Path(upload_filename).name
        if not filename or Path(filename).suffix.lower() != ".xml":
            raise FilePolicyError("Yalnızca .xml uzantılı e-belge dosyaları yüklenebilir.")
        if not contents:
            raise FilePolicyError("Boş bir XML dosyası yüklenemez.")
        if len(contents) > self._max_upload_bytes:
            raise FilePolicyError("Dosya izin verilen boyut sınırını aşıyor.")

        job_id = uuid4().hex
        job_directory = self._originals_root / job_id
        job_directory.mkdir(parents=True, exist_ok=False)
        destination = job_directory / filename
        temporary = job_directory / f".{filename}.uploading"
        temporary.write_bytes(contents)
        temporary.replace(destination)

        return StoredDocument(
            job_id=job_id,
            original_filename=filename,
            path=destination,
            sha256=sha256(contents).hexdigest(),
            size_bytes=len(contents),
        )
