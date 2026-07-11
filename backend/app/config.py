"""Application configuration.

Everything is driven by environment variables so the same image runs against a
local MinIO bucket in development and S3 / GCS in production. The only thing
that changes between environments is ``LANCEDB_URI`` and the credentials.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

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

    # GCS credential JSON path (only used for gs:// URIs). LanceDB's object-store
    # layer needs this passed explicitly; relying on GOOGLE_APPLICATION_CREDENTIALS
    # alone is not enough in local Docker ingestion.
    google_service_account: str | None = None
    google_application_credentials: str | None = None

    # --- Embeddings ---------------------------------------------------------
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    # Hugging Face token for rate limits / gated models. HF_TOKEN is also
    # supported because the hub itself recognizes it.
    huggingface_token: str | None = None
    hf_token: str | None = None
    # bge models recommend a short instruction prefix for retrieval queries.
    query_instruction: str = "Represent this sentence for searching relevant wines: "

    # --- LLM explanation layer ----------------------------------------------
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
        if self.lancedb_uri.startswith("gs://"):
            credential_path = self.google_service_account or self.google_application_credentials
            if credential_path:
                # Object-store distinguishes service-account JSON from user ADC.
                # Local `gcloud auth application-default login` creates an
                # `authorized_user` file, not a service-account file. Do not set
                # GOOGLE_SERVICE_ACCOUNT to an authorized_user ADC file.
                try:
                    credential_type = json.loads(Path(credential_path).read_text()).get("type")
                except Exception:
                    credential_type = None
                if credential_type == "service_account":
                    return {"google_service_account": credential_path}
                return {"google_application_credentials": credential_path}
        return None

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
