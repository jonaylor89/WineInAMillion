"""Wine in a Million — 2026 backend.

A semantic wine recommender that stores embeddings in a LanceDB table living
directly on object storage (MinIO / S3 / GCS) and serves recommendations via
FastAPI, with a streaming LLM layer that explains *why* each wine fits.
"""

__version__ = "1.0.0"
