from faturaguard.services.source_backed_explanation import (
    DeterministicSourceGenerator,
    FallbackExplanationGenerator,
    GeminiStructuredGenerator,
    GroqStructuredGenerator,
)
from scripts.run_demo_preflight import _chain_names


def test_preflight_formats_fallback_chain_without_secret_values() -> None:
    generator = FallbackExplanationGenerator(
        GeminiStructuredGenerator("gemini-key", "gemini-test"),
        FallbackExplanationGenerator(
            GroqStructuredGenerator("groq-key", "openai/gpt-oss-120b"),
            DeterministicSourceGenerator(),
        ),
    )

    names = _chain_names(generator)

    assert names == [
        "GeminiStructuredGenerator",
        "GroqStructuredGenerator",
        "DeterministicSourceGenerator",
    ]
