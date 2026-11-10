"""Chroma semantic retrieval, BM25 lexical retrieval ve açıklanabilir rerank."""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from faturaguard.services.official_rag import TOKEN_PATTERN, RagChunk

DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"


def tokenize(value: str) -> list[str]:
    """Türkçe karakterleri koruyarak retrieval için basit token üretir."""
    return TOKEN_PATTERN.findall(value.lower())


class Embedder(Protocol):
    def embed_documents(self, documents: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, query: str) -> list[float]: ...


class SentenceTransformerEmbedder:
    """Yerel/indirilebilir çok dilli embedding modeli için dar adaptör."""

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        cache_directory: Path = Path("data/models"),
        allow_model_download: bool = False,
    ) -> None:
        self.model_name = model_name
        self.cache_directory = cache_directory
        self.allow_model_download = allow_model_download
        self._model = None

    def embed_documents(self, documents: Sequence[str]) -> list[list[float]]:
        return self._encode([f"passage: {document}" for document in documents])

    def embed_query(self, query: str) -> list[float]:
        return self._encode([f"query: {query}"])[0]

    def _encode(self, values: list[str]) -> list[list[float]]:
        os.environ.setdefault("HF_HOME", str(self.cache_directory / "hf_home"))
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError("Embedding için sentence-transformers kurulmalıdır.") from error
        if self._model is None:
            self.cache_directory.mkdir(parents=True, exist_ok=True)
            self._model = SentenceTransformer(
                self.model_name,
                cache_folder=str(self.cache_directory),
                local_files_only=not self.allow_model_download,
            )
        return self._model.encode(values, normalize_embeddings=True).tolist()


@dataclass(frozen=True, slots=True)
class ScoredChunk:
    chunk: RagChunk
    score: float


@dataclass(frozen=True, slots=True)
class RetrievedEvidence:
    chunk: RagChunk
    semantic_score: float
    lexical_score: float
    exact_term_score: float
    rerank_score: float


class ChromaSemanticStore:
    """Doğrulanmış GİB chunks'larını yerel kalıcı Chroma koleksiyonunda saklar."""

    def __init__(
        self, persist_path: Path, embedder: Embedder, collection_name: str = "gib_official"
    ) -> None:
        self._persist_path = persist_path
        self._embedder = embedder
        self._collection_name = collection_name

    def rebuild(self, chunks: Sequence[RagChunk]) -> int:
        chromadb = self._chromadb()
        client = chromadb.PersistentClient(path=str(self._persist_path))
        try:
            client.delete_collection(self._collection_name)
        except Exception:  # Koleksiyon ilk kez oluşturuluyor olabilir.
            pass
        collection = client.create_collection(
            self._collection_name, metadata={"hnsw:space": "cosine"}
        )
        for start in range(0, len(chunks), 32):
            batch = chunks[start : start + 32]
            collection.add(
                ids=[self._chunk_id(chunk) for chunk in batch],
                documents=[chunk.text for chunk in batch],
                embeddings=self._embedder.embed_documents([chunk.text for chunk in batch]),
                metadatas=[
                    {
                        "source_id": chunk.source_id,
                        "source_title": chunk.source_title,
                        "source_url": chunk.source_url,
                        "page": chunk.page,
                    }
                    for chunk in batch
                ],
            )
        return len(chunks)

    def search(
        self, query: str, limit: int = 10, where: dict[str, str] | None = None
    ) -> list[ScoredChunk]:
        chromadb = self._chromadb()
        client = chromadb.PersistentClient(path=str(self._persist_path))
        collection = client.get_collection(self._collection_name)
        result = collection.query(
            query_embeddings=[self._embedder.embed_query(query)],
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        documents = result["documents"][0] if result["documents"] else []
        metadatas = result["metadatas"][0] if result["metadatas"] else []
        distances = result["distances"][0] if result["distances"] else []
        return [
            ScoredChunk(
                chunk=RagChunk(
                    source_id=metadata["source_id"],
                    source_title=metadata["source_title"],
                    source_url=metadata["source_url"],
                    page=int(metadata["page"]),
                    text=document,
                ),
                score=1 / (1 + float(distance)),
            )
            for document, metadata, distance in zip(documents, metadatas, distances, strict=True)
        ]

    @staticmethod
    def _chunk_id(chunk: RagChunk) -> str:
        identity = f"{chunk.source_id}:{chunk.page}:{chunk.text}".encode()
        return sha256(identity).hexdigest()

    @staticmethod
    def _chromadb():
        try:
            import chromadb
        except ImportError as error:
            raise RuntimeError("Vektör araması için chromadb kurulmalıdır.") from error
        return chromadb


class Bm25LexicalRetriever:
    """Kodlar, XML elementleri ve teknik terimler için lexical retrieval."""

    def __init__(self, chunks: Sequence[RagChunk]) -> None:
        try:
            from rank_bm25 import BM25Okapi
        except ImportError as error:
            raise RuntimeError("Lexical retrieval için rank-bm25 kurulmalıdır.") from error
        self._chunks = list(chunks)
        self._bm25 = BM25Okapi([tokenize(chunk.text) for chunk in self._chunks])

    def search(self, query: str, limit: int = 10) -> list[ScoredChunk]:
        scores = self._bm25.get_scores(tokenize(query))
        ordered = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:limit]
        return [
            ScoredChunk(self._chunks[index], float(score)) for index, score in ordered if score > 0
        ]


class HybridRetriever:
    """Semantic ve lexical adayları birleştirip anlaşılır bir puanla tekrar sıralar."""

    def __init__(self, semantic_store, lexical_retriever) -> None:
        self._semantic_store = semantic_store
        self._lexical_retriever = lexical_retriever

    def search(
        self, query: str, limit: int = 5, source_id: str | None = None
    ) -> list[RetrievedEvidence]:
        where = {"source_id": source_id} if source_id else None
        semantic = self._semantic_store.search(query, limit=12, where=where)
        lexical = self._lexical_retriever.search(query, limit=12)
        if source_id:
            lexical = [item for item in lexical if item.chunk.source_id == source_id]

        semantic_scores = {item.chunk: item.score for item in semantic}
        lexical_scores = {item.chunk: item.score for item in lexical}
        maximum_lexical = max(lexical_scores.values(), default=1.0)
        query_tokens = set(tokenize(query))
        evidence: list[RetrievedEvidence] = []
        for chunk in set(semantic_scores) | set(lexical_scores):
            semantic_score = semantic_scores.get(chunk, 0.0)
            lexical_score = lexical_scores.get(chunk, 0.0) / maximum_lexical
            chunk_tokens = set(tokenize(chunk.text))
            exact_term_score = len(query_tokens & chunk_tokens) / max(len(query_tokens), 1)
            rerank_score = (
                (0.55 * semantic_score) + (0.30 * lexical_score) + (0.15 * exact_term_score)
            )
            evidence.append(
                RetrievedEvidence(
                    chunk, semantic_score, lexical_score, exact_term_score, rerank_score
                )
            )
        return sorted(evidence, key=lambda item: item.rerank_score, reverse=True)[:limit]
