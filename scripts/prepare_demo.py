"""Git klonundan demo varlıklarını hazırlar; LLM çağırmaz, mevcut işleri silmez."""

import argparse
import hashlib
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx

from faturaguard.services.hybrid_retrieval import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_REVISION,
    ChromaSemanticStore,
    SentenceTransformerEmbedder,
)
from faturaguard.services.official_rag import OfficialRagIndexer, PdfTextExtractor
from faturaguard.services.official_source_catalog import OfficialSourceCatalog, SourcePolicyError

if __package__ in (None, ""):
    from generate_arithmetic_demo_fixtures import generate
else:
    from scripts.generate_arithmetic_demo_fixtures import generate

ROOT = Path(__file__).resolve().parents[1]
MAX_SOURCE_BYTES = 100 * 1024 * 1024


def download_source(catalog, source, *, client=None):
    """Allowlist ve sabit hash; değişen kaynak kendiliğinden güvenilir sayılmaz."""
    target = catalog.local_path(source).resolve()
    raw = (catalog._catalog_path.parent / "raw").resolve()
    if not target.is_relative_to(raw):
        raise SourcePolicyError("Kaynak yolu raw dizininden çıkamaz.")
    parsed = urlparse(source.url)
    if parsed.scheme != "https" or parsed.hostname not in {"ebelge.gib.gov.tr", "www.gib.gov.tr"}:
        raise SourcePolicyError("Yalnızca resmî HTTPS kaynakları indirilebilir.")
    if not source.expected_sha256:
        raise SourcePolicyError("Kaynak hash'i tanımlı değil.")
    target.parent.mkdir(parents=True, exist_ok=True)
    owned = client is None
    client = client or httpx.Client(timeout=60, follow_redirects=False)
    temp = None
    try:
        with client.stream("GET", source.url) as response:
            response.raise_for_status()
            if response.is_redirect:
                raise SourcePolicyError("Kaynak yönlendirmesi elle incelenmeli.")
            digest, count = hashlib.sha256(), 0
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                temp = Path(stream.name)
                for chunk in response.iter_bytes():
                    count += len(chunk)
                    if count > MAX_SOURCE_BYTES:
                        raise SourcePolicyError("Kaynak boyut sınırını aşıyor.")
                    stream.write(chunk)
                    digest.update(chunk)
            if digest.hexdigest() != source.expected_sha256.lower():
                raise SourcePolicyError("Kaynak SHA-256 eşleşmedi; dosya veya envanter değiştirilmedi.")
            temp.replace(target)
            temp = None
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
        if owned:
            client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-sources", action="store_true", help="Eksik GİB dosyalarını indir.")
    parser.add_argument("--download-model", action="store_true", help="Sabit sürümlü açık embedding modelini indir.")
    parser.add_argument("--fixtures-only", action="store_true", help="Sadece test XML örneklerini üret; ağ kullanmaz.")
    args = parser.parse_args()
    os.chdir(ROOT)
    fixtures = generate()
    print(f"Doğrulanmış örnek XML: {len(fixtures)}")
    if args.fixtures_only:
        return
    catalog = OfficialSourceCatalog(ROOT / "resources/gib/official_sources.json")
    verified = set(catalog.verified_local_sources())
    for source in catalog.sources:
        if not source.local_file or not source.expected_sha256 or source in verified:
            continue
        if not args.download_sources:
            raise SystemExit("Eksik/hash'i farklı GİB kaynağı var. --download-sources ile açıkça indirin.")
        print("Kaynak hazırlanıyor:", source.source_id)
        download_source(catalog, source)
    index = OfficialRagIndexer(catalog, PdfTextExtractor()).build()
    if not index.chunks:
        raise SystemExit("Resmî kaynak indeksi boş; hazırlık durduruldu.")
    if args.download_model:
        from huggingface_hub import snapshot_download

        snapshot_download(repo_id=DEFAULT_EMBEDDING_MODEL, revision=DEFAULT_EMBEDDING_REVISION,
                          cache_dir=str(ROOT / "data/models"),
                          allow_patterns=["*.json", "*.txt", "*.model", "*.safetensors"])
    chunks_path = ROOT / "data/rag/official_gib_chunks.json"
    index.save(chunks_path)
    try:
        count, total = ChromaSemanticStore(ROOT / "data/chroma", SentenceTransformerEmbedder()).sync(index.chunks)
    except (OSError, RuntimeError) as error:
        raise SystemExit("Embedding hazır değil. --download-model ile açıkça indirin veya yerel cache'i taşıyın.") from error
    if count != total:
        raise SystemExit("Chroma indeksi eksik; hazırlık komutunu yeniden çalıştırın.")
    print(f"Hazır: {len(index.chunks)} kaynak parçası, Chroma {count}/{total}. LLM çağrısı yapılmadı.")


if __name__ == "__main__":
    main()
