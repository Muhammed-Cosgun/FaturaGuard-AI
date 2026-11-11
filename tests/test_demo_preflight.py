from faturaguard.services.source_backed_explanation import (
    DeterministicSourceGenerator,
    FallbackExplanationGenerator,
)
from scripts.run_demo_preflight import _chain_names


def test_preflight_formats_fallback_chain_without_secret_values() -> None:
    generator = FallbackExplanationGenerator(
        DeterministicSourceGenerator(), DeterministicSourceGenerator()
    )

    names = _chain_names(generator)

    assert names == [
        "FallbackExplanationGenerator",
        "DeterministicSourceGenerator",
    ]
