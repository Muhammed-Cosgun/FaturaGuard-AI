import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from faturaguard.services.hybrid_retrieval import (
    DEFAULT_EMBEDDING_REVISION,
    SentenceTransformerEmbedder,
)
from faturaguard.services.official_source_catalog import OfficialSourceCatalog, SourcePolicyError
from scripts.check_submission import markdown_issues, secret_signature
from scripts.prepare_demo import download_source


def catalog(tmp_path, payload=b"official PDF"):
    target = tmp_path / "sources.json"
    target.write_text(json.dumps({"policy": {"allowed_domains": ["ebelge.gib.gov.tr"]},
        "sources": [{"id": "test", "title": "test", "status": "retrieved",
          "url": "https://ebelge.gib.gov.tr/document.pdf", "local_file": "raw/document.pdf",
          "sha256": hashlib.sha256(payload).hexdigest()}]}), encoding="utf-8")
    return OfficialSourceCatalog(target)


def test_official_download_is_hash_verified_and_atomic(tmp_path):
    value = b"official PDF"
    sources = catalog(tmp_path)
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=value)))
    download_source(sources, sources.sources[0], client=client)
    assert len(sources.verified_local_sources()) == 1


@pytest.mark.parametrize("mode", ["wrong_hash", "too_large", "redirect"])
def test_invalid_download_preserves_existing_source_and_cleans_temporary_files(tmp_path, monkeypatch, mode):
    sources = catalog(tmp_path)
    original = tmp_path / "raw/document.pdf"
    original.parent.mkdir()
    original.write_bytes(b"original backup")
    if mode == "too_large":
        monkeypatch.setattr("scripts.prepare_demo.MAX_SOURCE_BYTES", 2)
    response = httpx.Response(302, headers={"Location": "https://example.com"}) if mode == "redirect" else httpx.Response(200, content=b"untrusted")
    with httpx.Client(transport=httpx.MockTransport(lambda request: response)) as client:
        with pytest.raises((SourcePolicyError, httpx.HTTPStatusError)):
            download_source(sources, sources.sources[0], client=client)
    assert original.read_bytes() == b"original backup"
    assert list(original.parent.iterdir()) == [original]


def test_official_source_path_cannot_escape_raw_directory(tmp_path):
    sources = catalog(tmp_path)
    from dataclasses import replace

    escaped = replace(sources.sources[0], local_file="../outside.pdf")
    sources._sources = (escaped,)
    with pytest.raises(SourcePolicyError):
        download_source(sources, escaped)


def test_markdown_link_validation_handles_unicode_and_code_fences(tmp_path):
    target = tmp_path / "türkçe dosya.md"
    target.write_text("# Başlık", encoding="utf-8")
    page = tmp_path / "README.md"
    page.write_text("[local](<türkçe%20dosya.md>)\n```\n[x](ignored)\n```\n[remote](https://example.com)\n[bad](missing.md)", encoding="utf-8")
    issues = markdown_issues(page, tmp_path)
    assert len(issues) == 1 and issues[0]["target"] == "missing.md"


def test_secret_detection_does_not_require_printing_key_values():
    assert secret_signature(b"AIza" + b"x" * 35)
    assert secret_signature(b"gsk_" + b"x" * 40)
    assert not secret_signature(b'GEMINI_API_KEY="your-key-here"')


def test_preparation_runs_as_documented_script_in_clean_directory(tmp_path):
    root = Path(__file__).resolve().parents[1]
    for name in ["scripts/prepare_demo.py", "scripts/generate_arithmetic_demo_fixtures.py",
                 "resources/fixtures/baseline_invoice.xml"]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    result = subprocess.run([sys.executable, "scripts/prepare_demo.py", "--fixtures-only"],
                            cwd=tmp_path, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert len(list((tmp_path / "data/demo-fixtures").glob("*.xml"))) == 3


@pytest.mark.parametrize("download", [False, True])
def test_embedding_uses_pinned_revision_and_never_trusts_remote_code(tmp_path, monkeypatch, download):
    captured = {}

    class FakeModel:
        def __init__(self, model, **kwargs):
            captured.update(kwargs)

        def encode(self, *args, **kwargs):
            return SimpleNamespace(tolist=lambda: [[1.0]])

    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=FakeModel))
    embedder = SentenceTransformerEmbedder(cache_directory=tmp_path / "cache", allow_model_download=download)
    assert embedder.embed_query("test") == [1.0]
    assert captured["revision"] == DEFAULT_EMBEDDING_REVISION
    assert captured["trust_remote_code"] is False
    assert captured["local_files_only"] is not download
