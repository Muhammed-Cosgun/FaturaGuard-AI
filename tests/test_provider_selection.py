from dataclasses import replace

from faturaguard.config import settings
from faturaguard.main import _select_correction_planner, _select_explanation_generator
from faturaguard.services.source_backed_explanation import (
    CohereStructuredGenerator,
    DeterministicCorrectionPlanGenerator,
    DeterministicSourceGenerator,
    FallbackCorrectionPlanGenerator,
    FallbackExplanationGenerator,
    GeminiCorrectionPlanGenerator,
    GeminiStructuredGenerator,
    GroqStructuredGenerator,
    OllamaStructuredGenerator,
)


def test_auto_provider_chain_is_gemini_then_groq_then_deterministic() -> None:
    app_settings = replace(
        settings,
        llm_provider="auto",
        gemini_api_key="gemini-test-key",
        groq_api_key="groq-test-key",
        cohere_api_key="cohere-test-key",
    )

    generator = _select_explanation_generator(app_settings)

    assert isinstance(generator, FallbackExplanationGenerator)
    assert isinstance(generator._primary, GeminiStructuredGenerator)
    assert isinstance(generator._fallback, FallbackExplanationGenerator)
    assert isinstance(generator._fallback._primary, GroqStructuredGenerator)
    assert isinstance(generator._fallback._fallback, DeterministicSourceGenerator)


def test_cohere_is_available_only_when_explicitly_selected() -> None:
    app_settings = replace(
        settings,
        llm_provider="cohere",
        cohere_api_key="cohere-test-key",
        groq_api_key="groq-test-key",
    )

    generator = _select_explanation_generator(app_settings)

    assert isinstance(generator, FallbackExplanationGenerator)
    assert isinstance(generator._primary, CohereStructuredGenerator)
    assert isinstance(generator._fallback, FallbackExplanationGenerator)
    assert isinstance(generator._fallback._primary, GroqStructuredGenerator)


def test_local_mode_never_constructs_api_provider_chain() -> None:
    app_settings = replace(
        settings,
        llm_provider="local",
        gemini_api_key="gemini-test-key",
        groq_api_key="groq-test-key",
    )

    generator = _select_explanation_generator(app_settings)

    assert isinstance(generator, OllamaStructuredGenerator)


def test_correction_planner_uses_short_independent_timeout_budget() -> None:
    app_settings = replace(
        settings,
        llm_provider="auto",
        gemini_api_key="gemini-test-key",
        groq_api_key="groq-test-key",
        correction_plan_timeout_seconds=6.0,
    )

    planner = _select_correction_planner(app_settings)

    assert isinstance(planner, FallbackCorrectionPlanGenerator)
    assert isinstance(planner._primary, GeminiCorrectionPlanGenerator)
    assert planner._primary._timeout_seconds == 6.0
    assert isinstance(planner._fallback, FallbackCorrectionPlanGenerator)
    assert planner._fallback._primary._timeout_seconds == 6.0
    assert isinstance(planner._fallback._fallback, DeterministicCorrectionPlanGenerator)
