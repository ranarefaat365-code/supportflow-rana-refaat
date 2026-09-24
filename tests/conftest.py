import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from scripts.issue_token import issue


@pytest.fixture
def setup(tmp_path):
    settings = Settings(
        _env_file=None,
        jwt_secret="test-only-secret-value-that-is-long-enough",
        database_url="sqlite:///" + str(tmp_path / "test.db"),
        qdrant_url="",
        qdrant_path=str(tmp_path / "qdrant"),
        artifact_dir=str(tmp_path / "traces"),
        model_mode="extractive",
        langfuse_public_key="",
        langfuse_secret_key="",
        status_url="",
    )
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as client:

        def headers(user):
            return {"Authorization": "Bearer " + issue(user, settings)}

        yield client, app.state.service, headers, settings
