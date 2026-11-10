from starlette.requests import Request

from faturaguard.main import create_app


def _app_and_route_endpoint(path: str):
    app = create_app()
    endpoint = next(route.endpoint for route in app.routes if getattr(route, "path", None) == path)
    return app, endpoint


def test_health_check_returns_application_status() -> None:
    _, endpoint = _app_and_route_endpoint("/health")
    response = endpoint()

    assert response == {"status": "ok", "version": "0.1.0"}


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
