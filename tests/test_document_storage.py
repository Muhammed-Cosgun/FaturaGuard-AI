from hashlib import sha256

import pytest

from faturaguard.services.document_storage import DocumentStorage, FilePolicyError


def test_store_original_preserves_contents_and_records_sha256(tmp_path) -> None:
    contents = b"<Invoice>test</Invoice>"
    storage = DocumentStorage(tmp_path, max_upload_bytes=1024)

    stored = storage.store_original(contents, "../ornek.xml")

    assert stored.original_filename == "ornek.xml"
    assert stored.path.read_bytes() == contents
    assert stored.sha256 == sha256(contents).hexdigest()
    assert stored.path.parent.name == stored.job_id


@pytest.mark.parametrize("filename", ["fatura.pdf", "", "fatura.XML.exe"])
def test_store_original_rejects_non_xml_filename(tmp_path, filename: str) -> None:
    storage = DocumentStorage(tmp_path, max_upload_bytes=1024)

    with pytest.raises(FilePolicyError):
        storage.store_original(b"<Invoice />", filename)


def test_store_original_rejects_oversize_document(tmp_path) -> None:
    storage = DocumentStorage(tmp_path, max_upload_bytes=4)

    with pytest.raises(FilePolicyError):
        storage.store_original(b"12345", "fatura.xml")
