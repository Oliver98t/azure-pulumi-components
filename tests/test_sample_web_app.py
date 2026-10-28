import importlib.util
import logging
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


APP_PATH = Path(__file__).resolve().parents[1] / "source" / "web-app" / "app.py"


def load_app():
    spec = importlib.util.spec_from_file_location("sample_web_app", APP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_configures_azure_monitor_with_application_logger(monkeypatch):
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "configured")
    with patch("azure.monitor.opentelemetry.configure_azure_monitor") as configure:
        module = load_app()

    configure.assert_called_once_with(logger_name="web_app")
    assert module.logger.level == logging.INFO


def test_local_greeting_and_console_logging_without_connection_string(
    monkeypatch, caplog,
):
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    with patch("azure.monitor.opentelemetry.configure_azure_monitor") as configure:
        module = load_app()
    configure.assert_not_called()
    assert "Azure Monitor telemetry is disabled" in caplog.text

    with caplog.at_level(logging.INFO, logger="web_app"):
        with TestClient(module.app) as client:
            response = client.get("/check")
            assert client.get("/").status_code == 404
            assert client.get("/docs").status_code == 200

    assert response.status_code == 200
    assert response.json() == {"message": "Hello from Azure Web App!"}
    assert response.headers["content-type"].startswith("application/json")
    assert "Serving the greeting" in caplog.text


@pytest.mark.parametrize(
    ("configured_origins", "origin"),
    [
        (None, "http://localhost:5173"),
        (
            " https://frontend.azurestaticapps.net, https://www.example.com ",
            "https://frontend.azurestaticapps.net",
        ),
        (
            " https://frontend.azurestaticapps.net, https://www.example.com ",
            "https://www.example.com",
        ),
    ],
)
def test_cors_allows_configured_origins(monkeypatch, configured_origins, origin):
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    if configured_origins is None:
        monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", configured_origins)
    module = load_app()

    with TestClient(module.app) as client:
        response = client.get("/check", headers={"Origin": origin})
        preflight = client.options(
            "/check",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Request-ID",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"message": "Hello from Azure Web App!"}
    assert response.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in response.headers
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin
    assert preflight.headers["access-control-allow-methods"] == "GET"
    assert preflight.headers["access-control-allow-headers"] == "X-Request-ID"


@pytest.mark.parametrize(
    ("origin", "method"),
    [
        ("https://untrusted.example", "GET"),
        ("http://localhost:5173", "GET"),
        ("https://frontend.azurestaticapps.net", "POST"),
    ],
)
def test_cors_rejects_disallowed_preflight(monkeypatch, origin, method):
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS", "https://frontend.azurestaticapps.net"
    )
    module = load_app()

    with TestClient(module.app) as client:
        response = client.options(
            "/check",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": method,
            },
        )
        greeting = client.get(
            "/check", headers={"Origin": "https://untrusted.example"}
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in greeting.headers


def test_telemetry_configuration_errors_are_not_suppressed(monkeypatch):
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "invalid")
    with patch(
        "azure.monitor.opentelemetry.configure_azure_monitor",
        side_effect=ValueError("Invalid connection string"),
    ):
        with pytest.raises(ValueError, match="Invalid connection string"):
            load_app()


def test_console_logs_use_stdout_and_filter_azure_sdk_noise(monkeypatch):
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import logging, logging.config, runpy, sys; "
            "config = runpy.run_path(sys.argv[2]); "
            "logging.config.dictConfig(config['LOGGING_CONFIG']); "
            "app = runpy.run_path(sys.argv[1]); "
            "app['hello'](); "
            "sdk = logging.getLogger('azure.core.pipeline.policies.http_logging_policy'); "
            "sdk.info('Routine SDK request'); "
            "sdk.warning('SDK warning retained'); "
            "sdk.error('SDK error retained'); "
            "logging.getLogger('uvicorn.error').info('Server started'); "
            "logging.getLogger('uvicorn.error').error('Server failure'); "
            "logging.getLogger('uvicorn.access').info('Request completed'); "
            "app['logger'].warning('Application warning'); "
            "app['logger'].critical('Application critical')",
            str(APP_PATH),
            str(APP_PATH.with_name("server.py")),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "INFO:web_app:Serving the greeting" in result.stdout
    assert "Routine SDK request" not in result.stdout
    assert "SDK warning retained" in result.stdout
    assert "SDK error retained" in result.stderr
    assert "Server started" in result.stdout
    assert "Request completed" in result.stdout
    assert "Application warning" in result.stdout
    assert "Server failure" in result.stderr
    assert "Application critical" in result.stderr
    assert "ERROR:" not in result.stdout
    assert "CRITICAL:" not in result.stdout
    assert "INFO:" not in result.stderr
    assert "WARNING:" not in result.stderr
