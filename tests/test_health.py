from starlette.requests import Request

from faturaguard.domain.correction import CorrectionJob
from faturaguard.domain.validation import ValidationReport, ValidationSummary
from faturaguard.main import create_app, format_turkey_time, templates


def _app_and_route_endpoint(path: str):
    app = create_app()
    endpoint = next(route.endpoint for route in app.routes if getattr(route, "path", None) == path)
    return app, endpoint


def test_health_check_returns_application_status() -> None:
    _, endpoint = _app_and_route_endpoint("/health")
    response = endpoint()

    assert response == {"status": "ok", "version": "0.1.0"}


def test_turkey_time_formatter_converts_utc_audit_timestamp() -> None:
    assert format_turkey_time("2026-11-10T15:11:33.508466+00:00") == "10.11.2026 18:11"


def test_home_page_is_available() -> None:
    app, endpoint = _app_and_route_endpoint("/")
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": [], "app": app})
    response = endpoint(request)

    assert response.status_code == 200
    assert b"FaturaGuard AI" in response.body


def test_history_page_is_available() -> None:
    app, endpoint = _app_and_route_endpoint("/history")
    request = Request(
        {"type": "http", "method": "GET", "path": "/history", "headers": [], "app": app}
    )
    response = endpoint(request)

    assert response.status_code == 200
    assert "İşlem geçmişi".encode() in response.body


def test_presentation_templates_compile() -> None:
    for template_name in ("home.html", "validation_result.html", "history.html", "report.html"):
        assert templates.get_template(template_name) is not None


def test_result_summary_distinguishes_current_counts_from_initial_record():
    app = create_app()
    request = Request({'type': 'http', 'method': 'GET', 'path': '/', 'headers': [], 'app': app})
    report = ValidationReport(original_filename='demo.xml', findings=[], summary=ValidationSummary(
        is_valid=True, error_count=0, warning_count=2, info_count=0, duration_ms=1))
    job = CorrectionJob(job_id='job', original_filename='demo.xml', original_path='original.xml',
                        original_sha256='hash', report=report)
    template = templates.get_template('validation_result.html')
    initial = template.render(request=request, report=report, job=job)
    initial_hero = initial.split('class="notice result-hero"')[1].split('</section>')[0]
    assert '<strong>2</strong><span>Uyarı</span>' in initial_hero
    job.corrected_report = report.model_copy(deep=True)
    job.corrected_report.summary.warning_count = 0
    corrected = template.render(request=request, report=report, job=job)
    hero = corrected.split('class="notice result-hero"')[1].split('</section>')[0]
    assert '<strong>0</strong><span>Uyarı</span>' in hero
    assert '<strong>2</strong><span>Uyarı</span>' not in hero
    assert 'İlk doğrulama: 0 hata, 2 uyarı' in hero
    assert 'DÜZELTİLMİŞ KOPYA · GÜNCEL SONUÇ' in hero
    assert 'İlk doğrulamanın bulguları' in corrected
    assert 'Önceki yanıtlar soruldukları andaki durumu anlatır' in corrected
