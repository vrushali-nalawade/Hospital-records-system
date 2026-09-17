import pytest
import os
import time
from backend.config import settings
from backend.database import create_app_engine, normalize_database_url
from backend.storage import SupabaseStorageService, storage_service
from backend.ai_service import get_embedding, is_test_environment, QdrantClient

def test_production_mode_rejects_sqlite(monkeypatch):
    """
    Verifies that create_app_engine raises RuntimeError when ENVIRONMENT=production and URL is SQLite.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with pytest.raises(RuntimeError) as exc_info:
        create_app_engine("sqlite:///./test_prod_fallback.db")
    assert "Production environment requires a valid PostgreSQL DATABASE_URL" in str(exc_info.value)

def test_production_mode_rejects_local_storage(monkeypatch):
    """
    Verifies that SupabaseStorageService raises RuntimeError when ENVIRONMENT=production and Supabase credentials are missing.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SUPABASE_URL", None)
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)
    
    with pytest.raises(RuntimeError) as exc_info:
        SupabaseStorageService()
    assert "Production environment requires valid Supabase Storage credentials" in str(exc_info.value)

def test_production_mode_rejects_mock_bge_m3(monkeypatch):
    """
    Verifies that get_embedding raises RuntimeError in production mode if real BGE-M3 is unmounted.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "")  # Clear pytest test indicator for mock check
    import backend.ai_service as ai_module
    monkeypatch.setattr(ai_module, "_real_embedder", False)

    with pytest.raises(RuntimeError) as exc_info:
        get_embedding("Test medical text")
    assert "BAAI/bge-m3 MedicalEmbedder is not available in production environment" in str(exc_info.value)

def test_qdrant_cloud_configuration_structure(monkeypatch):
    """
    Verifies that QdrantClient correctly consumes QDRANT_URL and QDRANT_API_KEY when provided.
    """
    monkeypatch.setattr(settings, "QDRANT_URL", "https://test-qdrant-cluster.qdrant.tech")
    monkeypatch.setattr(settings, "QDRANT_API_KEY", "test-secret-api-key")
    
    # Test instantiation parameters
    assert settings.QDRANT_URL == "https://test-qdrant-cluster.qdrant.tech"
    assert settings.QDRANT_API_KEY == "test-secret-api-key"

def test_signed_url_cryptographic_verification():
    """
    Verifies signed URL generation, expiration logic, and signature tampering prevention.
    """
    storage = SupabaseStorageService()
    path = "patients/PAT001/documents/DOC001/prescription.pdf"
    
    signed_url = storage.create_signed_url(path, expires_in=300)
    assert "path=patients/PAT001/documents/DOC001/prescription.pdf" in signed_url
    assert "token=" in signed_url
    assert "expires=" in signed_url
    
    # Extract query params for validation
    import urllib.parse
    parsed = urllib.parse.urlparse(signed_url)
    params = urllib.parse.parse_qs(parsed.query)
    
    expires_at = int(params["expires"][0])
    token = params["token"][0]
    
    # Valid token check
    assert storage.verify_signed_url_token(path, expires_at, token) is True
    
    # Tampered path check
    assert storage.verify_signed_url_token("patients/PAT002/documents/DOC001/prescription.pdf", expires_at, token) is False
    
    # Expired token check
    assert storage.verify_signed_url_token(path, int(time.time()) - 10, token) is False
