# HealthVault AI — PostgreSQL Architecture & Guide

This guide explains the relational database architecture of HealthVault AI, comparing PostgreSQL with SQLite, detailing the 8 database tables, and providing instructions for secure connections and read-only inspection.

---

## 1. What is PostgreSQL?

**PostgreSQL** is an advanced, enterprise-grade, open-source Object-Relational Database Management System (ORDBMS). It is renowned for its reliability, feature robustness, strict SQL compliance, and strong ACID (Atomicity, Consistency, Isolation, Durability) guarantees.

In HealthVault AI, PostgreSQL acts as the **source of truth** for all relational entities: user identities, patient records, doctor credentials, clinical visits, document metadata, patient-doctor consent agreements, asynchronous ingestion job states, and immutable security audit logs.

---

## 2. How PostgreSQL Differs from SQLite

| Architectural Dimension | SQLite (Local Embedded) | PostgreSQL (Supabase / Production) |
|---|---|---|
| **Architecture** | Serverless, embedded file library (`healthvault.db`). | Client-Server RDBMS; runs as a standalone daemon listening over TCP (default port `5432`). |
| **Concurrency & Write Locking** | Single-writer lock across the entire file. Concurrent writes queue or result in `OperationalError: database is locked`. | Multi-Version Concurrency Control (MVCC). Multiple transactions can read and write concurrently without locking entire tables. |
| **Type System & Strictness** | Type affinity (dynamic and lenient). Can store a string in an integer column. | Strict static typing. Strongly enforces data types (`VARCHAR`, `TIMESTAMP`, `BOOLEAN`, `INTEGER`, `FLOAT`). |
| **Networking & Cloud Access** | Local disk only. Cannot be securely queried across multiple distributed backend instances. | Fully network-accessible with SSL/TLS encryption (`sslmode=require`), connection pooling (PgBouncer), and remote cloud hosting (e.g. Supabase). |
| **Security & Compliance** | File-system permission-based. Lacks granular user roles, connection pooling, and Row-Level Security (RLS). | Enterprise role-based access control (RBAC), Row-Level Security (RLS), and SSL encryption essential for HIPAA-ready healthcare applications. |
| **Integrity & Constraints** | Foreign keys must be manually enabled (`PRAGMA foreign_keys = ON`). | Foreign key constraints, unique constraints, and cascade rules are strictly enforced at the engine level. |

---

## 3. How HealthVault AI Uses the Relational Database

HealthVault AI employs a **polyglot persistence architecture**:
1. **Relational Layer (PostgreSQL)**: Handles structured business logic, user authentication links, clinical metadata, document ingestion states, consent approvals/revocations, and audit access trails.
2. **Vector Layer (Qdrant)**: Stores high-dimensional dense vector embeddings (BGE-M3 1024-dimensional vectors) for medical semantic retrieval, RAG, and AI question answering.
3. **Blob/Storage Layer**: Stores original PDF and image files securely on disk/cloud storage.

### Data Flow Overview:
```mermaid
flowchart TD
    User([User: Patient / Doctor]) -->|API Request with Bearer Token| FastAPI[FastAPI Backend]
    FastAPI -->|Check Role & Consent| PG[(PostgreSQL Relational DB)]
    FastAPI -->|Upload Document| DiskStorage[Medical Document Storage]
    FastAPI -->|Queue Background Job| IngestionWorker[Ingestion Worker]
    IngestionWorker -->|Update Status: PROCESSING| PG
    IngestionWorker -->|Extract OCR & NLP Entities| Person2[OCR/NLP Pipeline]
    Person2 -->|Extract Visit & Lab Data| IngestionWorker
    IngestionWorker -->|Generate 1024d Dense Vectors| BGEM3[BGE-M3 Model]
    BGEM3 -->|Store Embeddings| Qdrant[(Qdrant Vector DB)]
    IngestionWorker -->|Update Status: READY, Job: COMPLETED| PG
```

---

## 4. The 8 HealthVault Relational Tables

### 4.1 `users`
- **Purpose**: Stores authenticated user identities synced with Firebase Authentication.
- **Key Columns**:
  - `id` (VARCHAR, PK): Firebase UID (e.g., `patient-demo-1`, `D001UID`).
  - `email` (VARCHAR, Unique, NOT NULL): User's login email.
  - `role` (VARCHAR, NOT NULL): System role (`PATIENT`, `DOCTOR`, `ADMIN`).
  - `created_at` (TIMESTAMP): Account registration timestamp.

### 4.2 `patients`
- **Purpose**: Patient profiles linked 1:1 with `users`.
- **Key Columns**:
  - `id` (VARCHAR, PK): HealthVault patient identifier (e.g. `P001`, `P002`).
  - `user_id` (VARCHAR, FK -> `users.id`, Unique, NOT NULL): Associated user account.
  - `name` (VARCHAR, NOT NULL): Patient's full name.
  - `created_at` (TIMESTAMP): Profile creation timestamp.

### 4.3 `doctors`
- **Purpose**: Physician profiles linked 1:1 with `users`.
- **Key Columns**:
  - `id` (VARCHAR, PK): HealthVault doctor identifier (e.g. `D001`).
  - `user_id` (VARCHAR, FK -> `users.id`, Unique, NOT NULL): Associated user account.
  - `name` (VARCHAR, NOT NULL): Physician's full name.
  - `specialty` (VARCHAR, Nullable): Medical specialty (e.g., `Cardiology`, `Pediatrics`).
  - `created_at` (TIMESTAMP): Profile creation timestamp.

### 4.4 `visits`
- **Purpose**: Clinical encounters and medical timeline anchors.
- **Key Columns**:
  - `visit_id` (VARCHAR, PK): Unique visit identifier (e.g. `VIS_DOC_89528DA5`).
  - `patient_id` (VARCHAR, FK -> `patients.id`, NOT NULL): Patient who attended the visit.
  - `date` (VARCHAR, NOT NULL): Clinical date of visit (e.g. `2026-07-15`).
  - `doctor_id` (VARCHAR, FK -> `doctors.id`, Nullable): Attending physician.
  - `created_at` (TIMESTAMP): Record creation timestamp.

### 4.5 `documents`
- **Purpose**: Medical document records (prescriptions, lab reports, discharge summaries).
- **Key Columns**:
  - `document_id` (VARCHAR, PK): Unique document identifier (e.g. `DOC_89528DA5`).
  - `patient_id` (VARCHAR, FK -> `patients.id`, NOT NULL): Document owner.
  - `visit_id` (VARCHAR, FK -> `visits.visit_id`, Nullable): Linked clinical encounter.
  - `storage_path` (VARCHAR, NOT NULL): File path or object store URI.
  - `document_type` (VARCHAR, NOT NULL): `prescription`, `lab_report`, `medical_record`.
  - `status` (VARCHAR): `UPLOADED`, `PROCESSING`, `INDEXING`, `READY`, `FAILED`.
  - `confidence` (FLOAT): OCR extraction confidence score (0.00 to 1.00).
  - `needs_review` (BOOLEAN): Flag indicating if manual clinician verification is required.
  - `created_at` (TIMESTAMP): Upload timestamp.
  - `processed_at` (TIMESTAMP, Nullable): Completion timestamp.

### 4.6 `consents`
- **Purpose**: Explicit patient-granted access authorizations to specific doctors.
- **Key Columns**:
  - `consent_id` (VARCHAR, PK): Unique consent token (e.g. `CON_A3E5559F`).
  - `patient_id` (VARCHAR, FK -> `patients.id`, NOT NULL): Granting patient.
  - `doctor_id` (VARCHAR, FK -> `doctors.id`, NOT NULL): Authorized doctor.
  - `permission` (VARCHAR, NOT NULL): Scope of access (`VIEW_RECORDS`, `VIEW_DOCUMENTS`, `ASK_AI`).
  - `status` (VARCHAR): `ACTIVE`, `REVOKED`, `EXPIRED`.
  - `expires_at` (TIMESTAMP, Nullable): Expiration deadline.
  - `created_at` (TIMESTAMP): Issuance timestamp.

### 4.7 `access_logs`
- **Purpose**: Tamper-evident audit trail for all security, read, query, and consent events.
- **Key Columns**:
  - `log_id` (INTEGER, PK, Autoincrement/SERIAL): Sequence ID.
  - `actor_id` (VARCHAR, NOT NULL): User ID initiating the operation.
  - `patient_id` (VARCHAR, Nullable): Target patient data affected.
  - `action` (VARCHAR, NOT NULL): `LOGIN`, `DOCUMENT_UPLOAD`, `DOCUMENT_VIEW`, `AI_QUERY`, `CONSENT_GRANTED`, `CONSENT_REVOKED`.
  - `status` (VARCHAR, NOT NULL): `ALLOWED` or `DENIED`.
  - `timestamp` (TIMESTAMP): Exact UTC event time.

### 4.8 `processing_jobs`
- **Purpose**: Asynchronous background pipeline job tracking.
- **Key Columns**:
  - `job_id` (VARCHAR, PK): Unique background job identifier (e.g. `JOB_DOC_89528DA5`).
  - `document_id` (VARCHAR, FK -> `documents.document_id`, NOT NULL): Target document.
  - `status` (VARCHAR): `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`.
  - `error_message` (VARCHAR, Nullable): Error details if failed.
  - `created_at` (TIMESTAMP): Job queued time.
  - `updated_at` (TIMESTAMP): Last state update time.

---

## 5. Entity-Relationship Diagram

```mermaid
erDiagram
    users ||--o| patients : "has profile"
    users ||--o| doctors : "has profile"
    patients ||--o{ visits : "attends"
    doctors ||--o{ visits : "attends"
    patients ||--o{ documents : "owns"
    visits ||--o{ documents : "groups"
    documents ||--o{ processing_jobs : "triggers"
    patients ||--o{ consents : "grants"
    doctors ||--o{ consents : "receives"
    users ||--o{ access_logs : "audited by (actor)"
```

---

## 6. How to Connect to the Database

### 6.1 Via Backend Environment Configuration (`.env`)
In `backend/.env`:
```env
# Supabase Direct Connection:
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres

# Or Supabase Transaction Pooler Connection (Port 6543):
# DATABASE_URL=postgresql://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

### 6.2 Via GUI Client (DBeaver, TablePlus, pgAdmin)
- **Host**: `db.[YOUR-PROJECT-REF].supabase.co`
- **Port**: `5432`
- **Database**: `postgres`
- **User**: `postgres`
- **Password**: `[YOUR-PASSWORD]`
- **SSL**: `Required`

### 6.3 Via Command-Line (`psql`)
```bash
psql "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"
```

---

## 7. Safe Data Inspection Practices

When analyzing clinical data:
1. **Always Use Read-Only Mode**: Ensure sessions do not hold uncommitted transaction locks.
2. **Never Execute Unbounded Queries**: In large tables (like `access_logs`), always specify `LIMIT 50` or filter with `WHERE timestamp >= ...`.
3. **Use the HealthVault Read-Only Inspection Tool**:
   ```bash
   python backend/inspect_database.py
   ```
   This tool automatically:
   - Verifies connectivity without modifying data.
   - Redacts sensitive credentials, passwords, and private keys.
   - Inspects column schemas, primary keys, and table row counts.
   - Traces the latest document, background job, and audit trail.
4. **Run the Integrity Verification Tool**:
   ```bash
   python backend/verify_database.py
   ```
   Verifies that foreign-key relationships remain 100% consistent across all 8 tables.
