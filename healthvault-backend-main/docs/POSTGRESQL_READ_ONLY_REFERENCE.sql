-- ==============================================================================
-- HEALTHVAULT AI — READ-ONLY POSTGRESQL QUERY REFERENCE FOR SQL LEARNERS
-- ==============================================================================
-- NOTE: ALL queries in this file are strictly READ-ONLY (SELECT statements).
-- Destructive commands (INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER) are
-- intentionally EXCLUDED to ensure zero risk to medical data integrity.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. DATABASE SCHEMA & INTROSPECTION QUERIES
-- ------------------------------------------------------------------------------

-- 1.1 List all user tables in the current PostgreSQL database schema
SELECT 
    table_schema, 
    table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- 1.2 Describe table structure, columns, data types, and nullability
SELECT 
    table_name,
    column_name, 
    data_type, 
    character_maximum_length,
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- 1.3 View primary key and foreign key constraints across all HealthVault tables
SELECT 
    tc.table_name, 
    tc.constraint_name, 
    tc.constraint_type, 
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
LEFT JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_type;


-- ------------------------------------------------------------------------------
-- 2. TABLE ROW COUNT SUMMARIES
-- ------------------------------------------------------------------------------

-- 2.1 Count records across each of the 8 HealthVault relational tables
SELECT 'users' AS table_name, COUNT(*) AS total_records FROM users
UNION ALL
SELECT 'patients', COUNT(*) FROM patients
UNION ALL
SELECT 'doctors', COUNT(*) FROM doctors
UNION ALL
SELECT 'visits', COUNT(*) FROM visits
UNION ALL
SELECT 'documents', COUNT(*) FROM documents
UNION ALL
SELECT 'consents', COUNT(*) FROM consents
UNION ALL
SELECT 'access_logs', COUNT(*) FROM access_logs
UNION ALL
SELECT 'processing_jobs', COUNT(*) FROM processing_jobs;


-- ------------------------------------------------------------------------------
-- 3. BASIC TABLE VIEWS (SINGLE TABLE QUERIES)
-- ------------------------------------------------------------------------------

-- 3.1 View all registered users (Firebase UID, email, role)
SELECT 
    id AS firebase_uid, 
    email, 
    role, 
    created_at 
FROM users 
ORDER BY created_at DESC;

-- 3.2 View all patient profiles
SELECT 
    id AS patient_id, 
    user_id, 
    name, 
    created_at 
FROM patients 
ORDER BY id;

-- 3.3 View all doctor profiles and medical specialties
SELECT 
    id AS doctor_id, 
    user_id, 
    name, 
    specialty, 
    created_at 
FROM doctors 
ORDER BY id;

-- 3.4 View clinical visits
SELECT 
    visit_id, 
    patient_id, 
    date AS clinical_date, 
    doctor_id, 
    created_at 
FROM visits 
ORDER BY date DESC;

-- 3.5 View uploaded medical documents
SELECT 
    document_id, 
    patient_id, 
    visit_id, 
    document_type, 
    status, 
    confidence, 
    needs_review, 
    created_at, 
    processed_at 
FROM documents 
ORDER BY created_at DESC;

-- 3.6 View patient consents granted to doctors
SELECT 
    consent_id, 
    patient_id, 
    doctor_id, 
    permission, 
    status, 
    expires_at, 
    created_at 
FROM consents 
ORDER BY created_at DESC;

-- 3.7 View system access and security audit logs
SELECT 
    log_id, 
    actor_id, 
    patient_id, 
    action, 
    status, 
    timestamp 
FROM access_logs 
ORDER BY log_id DESC 
LIMIT 50;

-- 3.8 View document background processing jobs
SELECT 
    job_id, 
    document_id, 
    status, 
    error_message, 
    created_at, 
    updated_at 
FROM processing_jobs 
ORDER BY created_at DESC;


-- ------------------------------------------------------------------------------
-- 4. TARGETED & FILTERED CLINICAL QUERIES
-- ------------------------------------------------------------------------------

-- 4.1 Find the latest uploaded document in the system
SELECT 
    document_id, 
    patient_id, 
    visit_id, 
    document_type, 
    status, 
    confidence, 
    created_at,
    storage_path
FROM documents 
ORDER BY created_at DESC 
LIMIT 1;

-- 4.2 Find all documents belonging to a specific patient (e.g. 'P001')
SELECT 
    document_id, 
    document_type, 
    status, 
    confidence, 
    needs_review, 
    created_at 
FROM documents 
WHERE patient_id = 'P001' 
ORDER BY created_at DESC;

-- 4.3 Find document processing status breakdown
SELECT 
    status, 
    COUNT(*) AS document_count,
    ROUND(AVG(confidence)::numeric, 3) AS average_confidence
FROM documents 
GROUP BY status 
ORDER BY document_count DESC;

-- 4.4 Find revoked or expired doctor consents
SELECT 
    consent_id, 
    patient_id, 
    doctor_id, 
    permission, 
    status, 
    created_at 
FROM consents 
WHERE status = 'REVOKED' 
   OR (expires_at IS NOT NULL AND expires_at < NOW())
ORDER BY created_at DESC;

-- 4.5 View audit history for a specific patient's records (e.g. 'P001')
SELECT 
    log_id, 
    actor_id, 
    action, 
    status, 
    timestamp 
FROM access_logs 
WHERE patient_id = 'P001' 
ORDER BY timestamp DESC;

-- 4.6 View unauthorized (DENIED) access attempts for security review
SELECT 
    log_id, 
    actor_id, 
    patient_id, 
    action, 
    timestamp 
FROM access_logs 
WHERE status = 'DENIED' 
ORDER BY timestamp DESC;


-- ------------------------------------------------------------------------------
-- 5. RELATIONAL JOIN QUERIES (MULTI-TABLE INTEGRATION)
-- ------------------------------------------------------------------------------

-- 5.1 JOIN patients with their uploaded documents
-- Shows patient name, document ID, file type, OCR status, and confidence
SELECT 
    p.id AS patient_id, 
    p.name AS patient_name, 
    d.document_id, 
    d.document_type, 
    d.status AS ingestion_status, 
    d.confidence, 
    d.created_at AS uploaded_at
FROM patients p 
JOIN documents d ON p.id = d.patient_id 
ORDER BY p.id, d.created_at DESC;

-- 5.2 JOIN patients with clinical visits and attending doctors
-- Links patient, encounter date, and attending physician's specialty
SELECT 
    p.id AS patient_id, 
    p.name AS patient_name, 
    v.visit_id, 
    v.date AS visit_date, 
    COALESCE(doc.name, 'Unassigned / Self-Service') AS doctor_name, 
    doc.specialty
FROM patients p 
JOIN visits v ON p.id = v.patient_id 
LEFT JOIN doctors doc ON v.doctor_id = doc.id 
ORDER BY v.date DESC;

-- 5.3 JOIN users with their security audit activity
-- Links actor user profile with their system action history
SELECT 
    u.id AS user_id, 
    u.email, 
    u.role, 
    a.action, 
    a.status AS access_result, 
    a.patient_id AS target_patient, 
    a.timestamp
FROM users u 
JOIN access_logs a ON u.id = a.actor_id 
ORDER BY a.timestamp DESC 
LIMIT 30;

-- 5.4 Comprehensive Document Lifecycle Trace: Document + Processing Job + Patient
SELECT 
    d.document_id, 
    p.name AS patient_name, 
    d.document_type, 
    d.status AS document_status, 
    j.status AS job_status, 
    j.error_message, 
    d.created_at, 
    d.processed_at
FROM documents d 
JOIN patients p ON d.patient_id = p.id 
LEFT JOIN processing_jobs j ON d.document_id = j.document_id 
ORDER BY d.created_at DESC;

-- 5.5 Doctor Consent Authorization Matrix
-- Links doctor name, patient name, and permission level
SELECT 
    c.consent_id, 
    p.name AS patient_name, 
    d.name AS doctor_name, 
    d.specialty, 
    c.permission, 
    c.status AS consent_status, 
    c.expires_at
FROM consents c 
JOIN patients p ON c.patient_id = p.id 
JOIN doctors d ON c.doctor_id = d.id 
ORDER BY c.created_at DESC;
