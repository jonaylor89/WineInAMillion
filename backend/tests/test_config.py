"""Lightweight tests that don't require the ML stack or network."""

import json

from app.config import Settings


def test_local_uri_has_no_storage_options():
    s = Settings(lancedb_uri="./data/lancedb")
    assert s.storage_options() is None


def test_s3_storage_options_for_minio():
    s = Settings(
        lancedb_uri="s3://wine/lancedb",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        aws_endpoint="http://localhost:9000",
        aws_allow_http=True,
    )
    opts = s.storage_options()
    assert opts["aws_endpoint"] == "http://localhost:9000"
    assert opts["allow_http"] == "true"
    assert opts["aws_access_key_id"] == "minioadmin"


def test_gcs_storage_options_for_service_account(tmp_path):
    credential = tmp_path / "sa.json"
    credential.write_text(json.dumps({"type": "service_account"}))
    s = Settings(
        lancedb_uri="gs://wine-bucket/lancedb",
        google_service_account=str(credential),
    )
    assert s.storage_options() == {"google_service_account": str(credential)}


def test_gcs_storage_options_for_user_adc(tmp_path):
    credential = tmp_path / "adc.json"
    credential.write_text(json.dumps({"type": "authorized_user"}))
    s = Settings(
        lancedb_uri="gs://wine-bucket/lancedb",
        google_application_credentials=str(credential),
    )
    assert s.storage_options() == {"google_application_credentials": str(credential)}


def test_cors_origin_list_splits():
    s = Settings(cors_origins="http://a.com, http://b.com")
    assert s.cors_origin_list() == ["http://a.com", "http://b.com"]
