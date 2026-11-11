"""Sunum öncesi yerel ortam ve güvenli sağlayıcı zinciri kontrolü."""

from pathlib import Path

from faturaguard.config import settings
from faturaguard.main import _select_explanation_generator
from faturaguard.services.source_backed_explanation import FallbackExplanationGenerator

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _chain_names(generator: object) -> list[str]:
    names: list[str] = []
    current = generator
    while isinstance(current, FallbackExplanationGenerator):
        names.append(type(current._primary).__name__)
        current = current._fallback
    names.append(type(current).__name__)
    return names


def main() -> None:
    required = [
        PROJECT_ROOT / "data" / "rag" / "official_gib_chunks.json",
        PROJECT_ROOT / "data" / "chroma",
    ]
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Eksik RAG varlığı: " + ", ".join(missing))

    generator = _select_explanation_generator(settings)
    print("RAG indeksi: hazır")
    print(f"LLM modu: {settings.llm_provider}")
    print("Gemini anahtarı: " + ("tanımlı" if settings.gemini_api_key else "tanımlı değil"))
    print("Groq anahtarı: " + ("tanımlı" if settings.groq_api_key else "tanımlı değil"))
    print("Aktif üretim zinciri: " + " → ".join(_chain_names(generator)))
    print("Preflight sonucu: hazır")


if __name__ == "__main__":
    main()
