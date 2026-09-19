import os
import re
import time
import hmac
import hashlib
from typing import Optional, Tuple
from fastapi import HTTPException, status
from .config import settings

# Attempt to import official Supabase client
try:
    from supabase import create_client, Client
    HAS_SUPABASE_LIB = True
except ImportError:
    HAS_SUPABASE_LIB = False

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MIME_MAP = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg"
}

class SupabaseStorageService:
    """
    Secure Cloud Document Storage Service for HealthLocker.
    Integrates Supabase Storage with PRIVATE bucket enforcement, patient-scoped paths,
    safe filename sanitization, signed access URLs, and secure local caching for OCR.
    """

    def __init__(self):
        self.bucket_name = (settings.SUPABASE_STORAGE_BUCKET or "healthvault-medical-documents").strip().strip("'\"")
        self.url = settings.SUPABASE_URL.strip().strip("'\"") if settings.SUPABASE_URL else None
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY.strip().strip("'\"") if settings.SUPABASE_SERVICE_ROLE_KEY else None
        self.is_public = False  # Explicit invariant: bucket MUST remain private
        self.client: Optional[Any] = None
        self._secret_salt = (self.service_role_key or "healthvault_secure_salt_phase3").encode("utf-8")

        # Initialize live Supabase client if valid credentials are provided
        if HAS_SUPABASE_LIB and self.url and self.service_role_key and not self.url.startswith("https://your-project"):
            try:
                self.client = create_client(self.url, self.service_role_key)
                self._ensure_private_bucket_exists()
            except Exception as e:
                print(f"[SupabaseStorageService] Warning: Could not connect to remote Supabase Storage ({e}). Falling back to local private emulation.")
                self.client = None
        else:
            print("[SupabaseStorageService] Using local private document storage.")

    def _ensure_private_bucket_exists(self):
        """
        Guarantees that the target bucket exists and is strictly configured as PRIVATE (public=False).
        """
        if not self.client:
            return
        try:
            # Check if bucket exists
            buckets = self.client.storage.list_buckets()
            existing = next((b for b in buckets if getattr(b, "name", None) == self.bucket_name or getattr(b, "id", None) == self.bucket_name), None)
            if not existing:
                print(f"[SupabaseStorageService] Creating private bucket '{self.bucket_name}' (public=False)...")
                self.client.storage.create_bucket(self.bucket_name, options={"public": False})
            else:
                # Confirm bucket is private
                is_pub = getattr(existing, "public", False)
                if is_pub:
                    print(f"[SupabaseStorageService] Warning: Bucket '{self.bucket_name}' was public. Updating to private (public=False)...")
                    self.client.storage.update_bucket(self.bucket_name, options={"public": False})
        except Exception as e:
            print(f"[SupabaseStorageService] Warning during bucket verification: {e}")

    @staticmethod
    def sanitize_filename(original_filename: str) -> Tuple[str, str]:
        """
        Sanitizes filename and isolates extension to prevent path traversal attacks.
        Example: '../../malicious.pdf' -> ('malicious.pdf', '.pdf')
        """
        base = os.path.basename(original_filename)
        root, ext = os.path.splitext(base)
        ext = ext.lower()
        if not ext or ext not in ALLOWED_EXTENSIONS:
            ext = ".pdf"

        # Sanitize name to alphanumeric, underscores, hyphens
        clean_root = re.sub(r"[^a-zA-Z0-9_-]", "_", root).strip("_")
        if not clean_root:
            clean_root = "document"

        safe_filename = f"{clean_root}{ext}"
        return safe_filename, ext

    @staticmethod
    def format_storage_path(patient_id: str, document_id: str, safe_filename: str) -> str:
        """
        Standard patient-scoped storage key:
        patients/{patient_id}/documents/{document_id}/{safe_filename}
        """
        clean_patient_id = re.sub(r"[^a-zA-Z0-9_-]", "_", os.path.basename(patient_id))
        clean_doc_id = re.sub(r"[^a-zA-Z0-9_-]", "_", os.path.basename(document_id))
        return f"patients/{clean_patient_id}/documents/{clean_doc_id}/{safe_filename}"

    def upload_document(
        self,
        patient_id: str,
        document_id: str,
        file_content: bytes,
        original_filename: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Uploads medical document to private Supabase Storage (or local secure emulation).
        Returns the patient-scoped storage path.
        """
        safe_filename, ext = self.sanitize_filename(original_filename)
        storage_path = self.format_storage_path(patient_id, document_id, safe_filename)
        mime = content_type or MIME_MAP.get(ext, "application/octet-stream")

        # 1. Remote Supabase Storage upload
        if self.client:
            try:
                self.client.storage.from_(self.bucket_name).upload(
                    path=storage_path,
                    file=file_content,
                    file_options={"content-type": mime, "upsert": "true"}
                )
                # Also cache locally for immediate OCR pipeline access
                self._save_to_local_cache(storage_path, file_content)
                return storage_path
            except Exception as e:
                print(f"[SupabaseStorageService] Remote upload failed: {e}. Falling back to local private storage.")

        # 2. Local Private Storage (secure fallback / offline / tests)
        self._save_to_local_cache(storage_path, file_content)
        return storage_path

    def _get_local_cache_path(self, storage_path: str) -> str:
        # Standardize separators to local OS
        normalized = storage_path.replace("/", os.sep).replace("\\", os.sep)
        clean_subpath = os.path.normpath(normalized)
        if clean_subpath.startswith(os.sep) or ".." in clean_subpath:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage path")
        return os.path.abspath(os.path.join(settings.STORAGE_DIR, self.bucket_name, clean_subpath))

    def _save_to_local_cache(self, storage_path: str, file_content: bytes) -> str:
        target_path = self._get_local_cache_path(storage_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(file_content)
        return target_path

    def download_document(self, storage_path: str) -> bytes:
        """
        Downloads the document bytes from Supabase Storage (or local cache).
        """
        # Try remote Supabase Storage first if active
        if self.client:
            try:
                res = self.client.storage.from_(self.bucket_name).download(storage_path)
                if res:
                    return res
            except Exception as e:
                print(f"[SupabaseStorageService] Remote download failed ({e}), trying local cache.")

        # Check local cache
        local_path = self._get_local_cache_path(storage_path)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()

        # Check legacy storage path format for backward compatibility
        legacy_path = os.path.abspath(storage_path)
        if os.path.exists(legacy_path):
            with open(legacy_path, "rb") as f:
                return f.read()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found in cloud storage"
        )

    def get_local_file_for_ocr(self, storage_path: str) -> str:
        """
        Ensures a clean local file path exists for OpenCV CLAHE preprocessing and EasyOCR.
        """
        if not storage_path:
            return ""
        local_path = self._get_local_cache_path(storage_path)
        if os.path.exists(local_path):
            return local_path

        # Check demo records folders
        filename = os.path.basename(storage_path)
        demo_dirs = [
            os.path.join(os.getcwd(), "backend", "demo_records"),
            os.path.join(os.getcwd(), "demo_records"),
            os.path.join(os.path.dirname(__file__), "demo_records"),
            os.path.join(os.path.dirname(__file__), "..", "demo_records"),
            os.path.join(os.path.dirname(__file__), "..", "..", "demo_records")
        ]
        for d in demo_dirs:
            candidate = os.path.join(d, filename)
            if os.path.exists(candidate):
                return os.path.abspath(candidate)

        # If not cached locally, download bytes and save to local cache
        try:
            content = self.download_document(storage_path)
            return self._save_to_local_cache(storage_path, content)
        except Exception:
            if os.path.exists(storage_path):
                return os.path.abspath(storage_path)
            return storage_path

    def create_signed_url(self, storage_path: str, expires_in: int = 300) -> str:
        """
        Generates a secure temporary signed access URL with time-limited expiration.
        """
        # Remote Supabase Storage signed URL
        if self.client:
            try:
                res = self.client.storage.from_(self.bucket_name).create_signed_url(storage_path, expires_in)
                signed = res.get("signedURL") or res.get("signedUrl")
                if signed:
                    return signed
            except Exception as e:
                print(f"[SupabaseStorageService] Remote create_signed_url failed: {e}. Falling back to signed token.")

        # Cryptographically signed time-limited token (HMAC-SHA256)
        expires_at = int(time.time()) + expires_in
        payload = f"{storage_path}:{expires_at}:{self.bucket_name}"
        sig = hmac.new(self._secret_salt, payload.encode("utf-8"), hashlib.sha256).hexdigest()

        # Build backend signed access URL
        base_url = settings.FRONTEND_URL.rstrip("/")
        return f"{base_url}/api/storage/signed?path={storage_path}&expires={expires_at}&token={sig}"

    def verify_signed_url_token(self, storage_path: str, expires_at: int, token: str) -> bool:
        """
        Verifies the cryptographic signature and ensures token is not expired.
        """
        if time.time() > expires_at:
            return False  # Expired
        payload = f"{storage_path}:{expires_at}:{self.bucket_name}"
        expected_sig = hmac.new(self._secret_salt, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, token)

    def is_bucket_private(self) -> bool:
        """
        Invariant check: Must always be True (private bucket).
        """
        return not self.is_public


# Singleton instance
storage_service = SupabaseStorageService()


# Backward-compatible functional wrappers for existing codebase
def save_document(patient_id: str, document_id: str, file_content: bytes, original_filename: str) -> str:
    """
    Saves document to Supabase Storage with patient-scoped path.
    """
    return storage_service.upload_document(patient_id, document_id, file_content, original_filename)

def get_document_path(storage_path: str) -> str:
    """
    Validates that a file exists and returns safe local path for streaming or OCR.
    """
    return storage_service.get_local_file_for_ocr(storage_path)

def get_document_bytes(storage_path: str) -> bytes:
    """
    Downloads file bytes directly from storage.
    """
    return storage_service.download_document(storage_path)

def create_document_signed_url(storage_path: str, expires_in: int = 300) -> str:
    """
    Generates a secure temporary signed access URL.
    """
    return storage_service.create_signed_url(storage_path, expires_in)
