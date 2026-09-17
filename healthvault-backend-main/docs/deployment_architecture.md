# HealthVault AI Cloud Deployment Architecture

This document specifies the recommended cloud deployment architecture, infrastructure sizing, hosting providers, and deployment steps for HealthVault AI in production.

---

## 1. System Topology Overview

```
                          ┌──────────────────────────┐
                          │   Next.js Frontend       │
                          │   (Vercel / Netlify)     │
                          └─────────────┬────────────┘
                                        │ (HTTPS / CORS)
                                        ▼
                          ┌──────────────────────────┐
                          │   FastAPI Backend API    │
                          │ (Render / Fly.io / GCP)  │
                          └────┬────────┬────────┬───┘
                               │        │        │
            ┌──────────────────┘        │        └──────────────────┐
            ▼                           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│  Supabase PostgreSQL │    │   Supabase Storage   │    │     Qdrant Cloud     │
│   (Relational DB)    │    │ (Private Med Bucket) │    │  (Vector Database)   │
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

---

## 2. Infrastructure Sizing & Provider Recommendations

### A. Backend API & AI Workloads (FastAPI)
* **Recommended Provider**: **Render Web Service** (Starter / Standard instance) or **Fly.io** / **Google Cloud Run**.
* **Minimum Specifications**:
  * **RAM**: 2 GB – 4 GB (Required for PyTorch, EasyOCR, and BAAI/bge-m3 transformer model weights).
  * **CPU**: 2+ Shared or Dedicated vCPUs.
* **Why Free-Tiers Fail for Heavy AI**:
  * Free tiers on platforms like Render (512MB RAM) or Vercel Serverless (1024MB RAM) will crash with Out-Of-Memory (OOM) when loading PyTorch model weights into memory.
  * Dedicated GPU/CPU instances or containerized workers (e.g. AWS ECS / Cloud Run with 4GB RAM) prevent memory exhaustion.

### B. Relational Database (Supabase PostgreSQL)
* **Provider**: **Supabase Managed PostgreSQL**.
* **Connection Pooling**: Use Supabase Session/Transaction pooler on Port `6543` or Port `5432` with `pool_pre_ping=True`.
* **Database URL Format**:
  ```env
  DATABASE_URL=postgresql+psycopg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require
  ```

### C. Medical Document Storage (Supabase Storage)
* **Provider**: **Supabase Storage**.
* **Bucket**: `healthvault-medical-documents` (Strictly **PRIVATE**, `public: False`).
* **Path Schema**: `patients/{patient_id}/documents/{document_id}/{filename}`.
* **Access Control**: Temporary signed URLs generated via backend (`SIGNED_URL_EXPIRY_SECONDS=300`).

### D. Vector Search Database (Qdrant Cloud)
* **Provider**: **Qdrant Cloud Cluster** (Free 1GB Cluster or Managed Dedicated Cluster).
* **Configuration**:
  ```env
  QDRANT_URL=https://[your-cluster-id].[region].qdrant.tech
  QDRANT_API_KEY=[your-qdrant-api-key]
  ```
* **Specs**: Collection `medical_records`, Vector Size `1024`, Distance `COSINE`. Mandatory payload indexing on `patient_id`.

### E. Frontend Application (Next.js 16)
* **Provider**: **Vercel** or **Netlify**.
* **Environment Variables**:
  * `NEXT_PUBLIC_API_URL=https://api.healthvault.example.com`
  * `NEXT_PUBLIC_FIREBASE_PROJECT_ID=...`
  * **ZERO** service-role keys exposed in frontend bundle.

---

## 3. Environment Variables Checklist (Backend Production)

| Variable | Description | Example / Note |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Environment flag | `production` |
| `DATABASE_URL` | Supabase Postgres URL | `postgresql+psycopg://...` |
| `SUPABASE_URL` | Supabase Cloud project URL | `https://[ref].supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Admin Key | Backend ONLY key |
| `SUPABASE_STORAGE_BUCKET` | Medical Bucket | `healthvault-medical-documents` |
| `QDRANT_URL` | Qdrant Cloud URL | `https://[cluster].qdrant.tech` |
| `QDRANT_API_KEY` | Qdrant API key | Secret key |
| `FRONTEND_URL` | Allowed CORS Origin | `https://healthvault.example.com` |
| `DOCTOR_ALLOWED_EMAIL_DOMAINS` | Institutional Doctor Domains | `demo.health,hospital.org,healthvault.com` |
