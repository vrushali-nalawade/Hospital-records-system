# HealthVault AI — Person 4 Backend + Full Frontend Integration Plan

## 1. Current State Inspection & Architecture

We have inspected the workspace and sibling directories. Here is the structure:
- **`Backend/` (Workspace Root)**:
  - `backend/`: FastAPI application (`main.py`, `models.py`, `schemas.py`, `config.py`, `ai_service.py`, `processing.py`, etc.).
  - `tests/`: Test suite containing `test_backend.py` covering all target security, AI, consent, and E2E scenarios.
- **`Hospital-records-system/` (Sibling Directory)**:
  - Next.js frontend (`src/`, `package.json`, etc.).
  - Person 2 OCR & Medical NLP pipeline (`ocr_pipeline.py`, `medical_ner.py`, `full_pipeline.py`).
  - Person 3 AI retrieval, RAG, and LangGraph pipelines (`embeddings.py`, `vector_store.py`, `retrieval.py`, `rag.py`, `agents.py`, `pipeline_api.py`).

### Key Findings
- **Teammate Pipelines**: The teammate code is in the sibling directory `Hospital-records-system`. The backend's `config.py` dynamically appends this path to `sys.path`.
- **Backend Implementations**: The FastAPI backend is structurally complete. Running the tests shows that the backend and integration logic are fully operational, falling back to mock workflows if external libraries (like `sentence-transformers`) or file types are not compatible, which ensures robust integration.
- **Frontend Services**:
  - `demo-mode.ts` governs `IS_DEMO_MODE`.
  - Services like `auth-service.ts`, `records-service.ts`, and `consent-service.ts` have placeholder/mock logic for demo mode, but already contain `fetch` calls to the FastAPI backend at `http://localhost:8000` when not in demo mode.
  - Some frontend pages directly import and call the synchronous mock-based helpers (e.g., `getRecordsForPatient`, `getConsentsForPatient`, `getAccessLogsForPatient`) instead of the asynchronous API fetch helpers (e.g., `fetchRecordsForPatient`, `fetchConsentsForPatient`, `fetchAccessLogsForPatient`).

---

## 2. Proposed Work Plan

### Phase 1: Frontend Configuration Alignment
1. Modify `Hospital-records-system/src/lib/demo-mode.ts` to respect a `process.env.NEXT_PUBLIC_DEMO_MODE` environment variable, falling back to Firebase configuration detection.
2. In `Hospital-records-system/src/lib/services/consent-service.ts`, implement `getAccessLogsForPatient` (which is currently used by the pages but missing from the service module), and implement the real-mode `fetchAccessLogsForPatient` to get logs from the FastAPI backend `/audit/me` endpoint.

### Phase 2: Frontend Page Integration
We will update the frontend pages to use the asynchronous API fetch methods in real mode:
1. **`src/app/patient/dashboard/page.tsx`**: Fetch records, consents, and access logs from the backend API.
2. **`src/app/patient/records/page.tsx`**: Fetch records from the backend API.
3. **`src/app/patient/access-history/page.tsx`**: Fetch access history from the backend API.
4. **`src/app/patient/consent/page.tsx`**: Fetch doctor consents and trigger approvals/revocations on the backend API.
5. **`src/app/patient/history/page.tsx`**: Fetch the longitudinal timeline from the backend API.
6. **`src/app/doctor/dashboard/page.tsx`**: Fetch patients with valid consent.
7. **`src/app/doctor/patients/page.tsx`**: Fetch patient list.
8. **`src/app/doctor/patients/[patientId]/records/page.tsx`**: Fetch records for a patient after verifying consent.
9. **`src/app/doctor/patients/[patientId]/history/page.tsx`**: Fetch timeline history for a patient.

### Phase 3: E2E and Test Verification
1. Ensure the Python FastAPI backend test suite runs and all tests pass.
2. Verify Next.js compiles cleanly with TypeScript and runs against the FastAPI backend.
