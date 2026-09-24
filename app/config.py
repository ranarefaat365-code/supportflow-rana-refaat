from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = "sqlite:///./runtime/supportflow.db"
    qdrant_url: str = ""
    qdrant_path: str = "./runtime/qdrant"
    jwt_secret: str = ""
    jwt_issuer: str = "supportflow-local"
    jwt_audience: str = "supportflow-api"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    model_mode: str = "extractive"
    embedding_mode: str = "hash"
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_cost_per_million: float = 0
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = ""
    input_cost_per_million: float = 0
    output_cost_per_million: float = 0
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"
    enable_evals: bool = False
    status_url: str = ""
    max_results: int = 4
    retrieval_threshold: float = 0.08
    artifact_dir: str = "./runtime/traces"

    def validate_runtime(self):
        if len(self.jwt_secret) < 32 or self.jwt_secret.startswith("CHANGE_ME"):
            # Example values are never valid authentication secrets.
            raise ValueError("JWT_SECRET must be at least 32 characters. Run python -m scripts.setup_local.")
        if self.embedding_mode not in {"hash", "api"}:
            raise ValueError("EMBEDDING_MODE must be hash or api")
        if self.embedding_mode == "api" and not self.embedding_api_key:
            raise ValueError("API embeddings require EMBEDDING_API_KEY")
        if self.model_mode not in {"extractive", "llm"}:
            raise ValueError("MODEL_MODE must be extractive or llm")
        if self.model_mode == "llm" and (not self.llm_api_key or not self.llm_model):
            raise ValueError("LLM mode requires LLM_API_KEY and LLM_MODEL")
