"""La plantilla compartida con Docker también debe permitir iniciar FastAPI."""

from pathlib import Path

from app.core.config import Settings


def test_env_example_can_be_loaded_by_backend(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    example = Path(__file__).resolve().parents[2] / ".env.example"
    configured = Settings(_env_file=example)
    assert configured.APP_VERSION == "1.1.0"
    assert configured.API_V1_PREFIX == "/api/v1"
