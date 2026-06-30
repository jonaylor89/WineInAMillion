"""Application configuration.

Everything is driven by environment variables so the same image runs against a
local MinIO bucket in development and S3 / GCS in production. The only thing
that changes between environments is ``LANCEDB_URI`` and the credentials.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Vector store -------------------------------------------------------
    # LanceDB connects directly to object storage. Examples:
    #   local dir   ->  ./data/lancedb
    #   MinIO / S3  ->  s3://wine/lancedb
    #   GCS         ->  gs://wine-bucket/lancedb
    lancedb_uri: str = "./data/lancedb"
    lancedb_table: str = "wines"

    # S3 / MinIO storage options (ignored for local dir or gs:// URIs).
    # For MinIO you set the endpoint + allow_http; for real S3 leave the
    # endpoint empty and rely on the region.
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-1"
    aws_endpoint: str | None = None  # e.g. http://localhost:9000 for MinIO
    aws_allow_http: bool = False

    # GCS service-account JSON path (only used for gs:// URIs).
    google_service_account: str | None = None

    # --- Embeddings ---------------------------------------------------------
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    # bge models recommend a short instruction prefix for retrieval queries.
    query_instruction: str = "Represent this sentence for searching relevant wines: "

    # --- LLM explanation layer (optional) -----------------------------------
    llm_enabled: bool = False
    llm_base_url: str | None = None  # OpenAI-compatible endpoint override
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"

    # --- API ----------------------------------------------------------------
    cors_origins: str = "http://localhost:5173"
    default_k: int = 5

    def storage_options(self) -> dict[str, str] | None:
        """Build LanceDB ``storage_options`` for the configured backend."""
        if self.lancedb_uri.startswith("s3://"):
            opts: dict[str, str] = {"aws_region": self.aws_region}
            if self.aws_access_key_id:
                opts["aws_access_key_id"] = self.aws_access_key_id
            if self.aws_secret_access_key:
                opts["aws_secret_access_key"] = self.aws_secret_access_key
            if self.aws_endpoint:
                opts["aws_endpoint"] = self.aws_endpoint
            if self.aws_allow_http:
                opts["allow_http"] = "true"
            return opts
        if self.lancedb_uri.startswith("gs://") and self.google_service_account:
            return {"google_service_account": self.google_service_account}
        return None

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
