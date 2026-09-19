import os
import sys
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Dynamically add the local ai_pipeline directory and sibling Hospital-records-system directory to sys.path
LOCAL_PIPELINE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai_pipeline"))
TEAMMATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Hospital-records-system"))

if os.path.exists(TEAMMATE_PATH) and TEAMMATE_PATH not in sys.path:
    sys.path.insert(0, TEAMMATE_PATH)
if os.path.exists(LOCAL_PIPELINE_PATH) and LOCAL_PIPELINE_PATH not in sys.path:
    sys.path.insert(0, LOCAL_PIPELINE_PATH)

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./healthvault.db"
    QDRANT_HOST: Optional[str] = None
    QDRANT_PORT: int = 6333
    FIREBASE_PROJECT_ID: str = "your-firebase-project-id"
    FIREBASE_CLIENT_EMAIL: str = "your-firebase-service-account-email"
    FIREBASE_PRIVATE_KEY: str = "-----BEGIN PRIVATE KEY-----\nyour-private-key-here\n-----END PRIVATE KEY-----\n"
    STORAGE_BUCKET: str = "healthvault-medical-documents"
    STORAGE_DIR: str = "backend/storage"
    FRONTEND_URL: str = "https://healthvault-frontend-seven.vercel.app"
    DOCTOR_ALLOWED_EMAIL_DOMAINS: str = "demo.health,hospital.org,healthvault.com,doctor.com"
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None
    QDRANT_STORAGE_DIR: str = "backend/qdrant_db"
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    ENVIRONMENT: str = "development"
    TESTING: bool = False

    # Hugging Face Spaces AI Microservice Endpoints
    HF_EMBEDDING_URL: Optional[str] = "https://vrushalily-healthvault-ai.hf.space"
    HF_RERANKER_URL: Optional[str] = "https://vrushalily-healthvault-ai.hf.space"
    HF_LLM_URL: Optional[str] = "https://vrushalily-healthvault-ai.hf.space"
    HF_API_TOKEN: Optional[str] = None      # HuggingFace Access Token if space is private
    OPENROUTER_API_KEY: Optional[str] = None # OpenRouter fallback for LLM synthesis
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"

    # Google Gemini Conversational RAG Generation
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Supabase Cloud Storage (Private Bucket & Signed URLs)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None  # Strictly backend-only, never sent to client
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "healthvault-medical-documents"
    SIGNED_URL_EXPIRY_SECONDS: int = 300  # 5 minutes default

    @property
    def cors_origins(self) -> list[str]:
        import re
        origins = {
            "https://healthvault-frontend-seven.vercel.app",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        }
        if self.FRONTEND_URL:
            for url in re.split(r"[,;\s]+", self.FRONTEND_URL.strip()):
                cleaned = url.strip().rstrip("/")
                if cleaned:
                    origins.add(cleaned)
        return sorted(list(origins))

    model_config = SettingsConfigDict(
        env_file=[os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")), ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

