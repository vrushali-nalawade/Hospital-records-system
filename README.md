# 🏥 HealthVault AI — Intelligent Clinical Health Locker & Medical RAG Platform

[![Next.js](https://img.shields.io/badge/Next.js-16.0-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.0-blue?style=for-the-badge&logo=react)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python)](https://python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6F00?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-1.5_Flash-8E75B2?style=for-the-badge&logo=google)](https://ai.google.dev/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-DC2626?style=for-the-badge&logo=qdrant)](https://qdrant.tech/)
[![Supabase](https://img.shields.io/badge/Supabase-Storage-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com/)
[![Firebase](https://img.shields.io/badge/Firebase-Auth-FFCA28?style=for-the-badge&logo=firebase)](https://firebase.google.com/)

---

## 📌 Overview

**HealthVault AI** is a privacy-first, intelligent digital health locker designed to solve the fragmentation of physical and digital medical records. It transforms messy handwritten prescriptions, lab reports, and hospital discharge summaries into structured, searchable health timelines and allows patients to query their longitudinal medical history using natural language without the risk of AI hallucinations.

---

## 📸 Screenshots & UI Tour

<div align="center">

### 🌐 1. Landing Page & Product Overview
![Landing Page](./docs/images/landing_page.png)
*Modern, glassmorphic landing page highlighting patient digital health lockers, consent tools, and AI comprehension.*

<br/>

### 🔐 2. Patient Authentication & Secure Onboarding
<p float="left">
  <img src="./docs/images/patient_login.png" width="48%" alt="Patient Login" />
  <img src="./docs/images/patient_registration.png" width="48%" alt="Patient Registration" />
</p>
*Secure Firebase user registration and token-based authentication with HIPAA-aligned patient data isolation.*

<br/>

### 🖥️ 3. Patient Dashboard & Health Locker
![HealthVault Dashboard](./docs/images/dashboard.png)
*Central dashboard displaying uploaded medical documents, consent status, doctor access logs, and recent activity.*

<br/>

### 📤 4. Document Ingestion & Categorization
![Upload Medical Record](./docs/images/upload_record.png)
*Upload interface supporting Prescriptions, Blood Reports, Lab Reports, Medical Scans, and Discharge Summaries.*

<br/>

### ⏳ 5. Longitudinal Medical History Timeline & Profile
<p float="left">
  <img src="./docs/images/medical_history_timeline.png" width="48%" alt="Medical History Timeline" />
  <img src="./docs/images/patient_profile.png" width="48%" alt="Patient Profile" />
</p>
*Chronological event stream tracking all past visits, consultations, and patient profile preferences.*

<br/>

### 🛡️ 6. Access History & Doctor Consent Management
![Access History & Consent](./docs/images/access_history_consent.png)
*Audit log giving patients granular control to review, approve, or revoke medical record access for healthcare providers.*

<br/>

### 💬 7. AI Health Assistant & Clinical Q&A
<p float="left">
  <img src="./docs/images/ai_assistant_initial.png" width="48%" alt="AI Assistant Initial Scope" />
  <img src="./docs/images/ai_assistant_chat.png" width="48%" alt="AI Assistant Response" />
</p>
*Interactive clinical query engine with configurable context scope (Whole Vault vs Specific Record) and suggested follow-ups.*

</div>

---

## 💬 Sample Grounded Conversation Flow

Here is an example interaction between a patient and the **HealthVault AI Assistant** powered by **Google Gemini 1.5 Flash** and the **LangGraph Hybrid RAG Engine**:

> **User:** *"What lifestyle changes or precautions are advised based on my recent records?"*

```markdown
Here is a clear summary of your recent health records in plain words:

---

### 🫀 Cardiology Prescription Summary
Your doctor evaluated you for **Essential Stage 2 Hypertension** (high blood pressure) and **Mixed Hyperlipidemia** (elevated blood cholesterol levels).

#### 💊 Prescribed Medications & How to Take Them
1. **Atorvastatin 20 mg (Cholesterol Medication / Statin)**
   • Dosage: 1 tablet once daily at bedtime.
   • Purpose: Lowers LDL ("bad") cholesterol and protects your blood vessels and heart.

2. **Amlodipine 5 mg (Blood Pressure Medication)**
   • Dosage: 1 tablet once daily in the morning.
   • Purpose: Relaxes blood vessels so blood flows smoothly, keeping blood pressure in a safe range.

3. **Aspirin 81 mg (Cardiovascular Protection)**
   • Dosage: 1 tablet once daily with food.
   • Purpose: Low-dose blood thinner to prevent clot formation and maintain cardiac health.

#### 💡 Practical Advice
• Maintain a low-sodium (low salt) diet and stay well hydrated.
• Check and log your blood pressure once or twice a week at home.

---

### 🩺 Gastroenterology Discharge Summary
Your physician evaluated you for **Peptic Ulcer Disease** and **Gastroesophageal Reflux Disease (GERD)**.

#### 💊 14-Day Triple Therapy Protocol
1. **Pantoprazole 40 mg (Acid Reducer)** — 1 tablet twice daily, 30 minutes before morning & evening meals.
2. **Amoxicillin 1000 mg (Antibiotic)** — 1 tablet twice daily with meals for 14 days.
3. **Clarithromycin 500 mg (Antibiotic)** — 1 tablet twice daily with meals for 14 days.

#### 💡 Practical Advice for Recovery
• Finish all antibiotics: Always complete the entire 14-day course.
• Dietary guidelines: Avoid spicy, fried, or highly acidic foods (citrus, vinegar, tomato). Avoid caffeine and alcohol.
• Meal habits: Eat smaller, more frequent meals.

---
📑 Citations & Verified Sources: `DOC_CC822310`, `DOC_23DAFB8E`, `DOC_F0D4A673`
💡 Suggested Follow-up Questions:
• What is my target blood pressure range?
• What low-sodium diet and lifestyle tips should I follow?
• Are there any side effects with these antibiotics?
• When should I schedule a follow-up test for H. pylori?
```

---

## ✨ Key Features

* **📷 4-Tier Resilient OCR Pipeline:**
  * **Tier 1:** Native PyMuPDF text layer extraction for digital PDFs ($<30\text{ms}$).
  * **Tier 2:** Remote Hugging Face ZeroGPU (NVIDIA A100) EasyOCR endpoint for handwriting ($<0.5\text{s}$).
  * **Tier 3:** Local lazy-loaded CPU EasyOCR fallback.
  * **Tier 4:** Deterministic rule-based fallback for demo templates.
* **🧪 Medical Named Entity Recognition (NER):** Extracts structured medications (drug, dosage, frequency), lab investigations (test name, observed value, unit, reference range), and doctor metadata.
* **🔍 Dual-Engine Hybrid Retrieval (RRF):** Fuses **1024-d Dense Semantic Embeddings (BGE-M3)** with **Sparse Keyword Matching (BM25Okapi)** using Reciprocal Rank Fusion ($k=60$).
* **🎯 Cross-Encoder Reranking:** Re-scores retrieved candidate chunks with `ms-marco-MiniLM-L-6-v2` to pass only top clinical evidence.
* **🛡️ Dual-Gate Hallucination Guardrails:**
  * **Pre-Generation Gate:** Verifies query medical entities exist in records before calling the LLM.
  * **Post-Generation Gate:** Fact-checks generated claims against source document n-grams to ensure near-zero medical fabrication.
* **🔒 Enterprise-Grade Security & Storage:**
  * Secure user isolation with **Firebase Authentication**.
  * Encrypted file hosting with **Supabase Private Storage** using 5-minute HMAC-signed URLs.

---

## 🏗️ Architecture & Pipeline Flow

```mermaid
flowchart TD
    A[User Uploads Prescription / Lab PDF] --> B[OpenCV CLAHE Pre-processing]
    B --> C{4-Tier OCR Pipeline}
    C -->|Native PDF| D1[PyMuPDF]
    C -->|Scanned / Image| D2[HF ZeroGPU EasyOCR A100]
    D1 & D2 --> E[Medical NER & Entity Structuring]
    
    E --> F[(Supabase Private Bucket)]
    E --> G[(PostgreSQL / SQLite Metadata)]
    E --> H[BGE-M3 Embeddings]
    H --> I[(Qdrant Vector DB)]
    
    J[User Asks Medical Question] --> K[LangGraph StateGraph Agent]
    K --> L[Hybrid Retrieval: BGE-M3 + BM25Okapi]
    L --> M[Reciprocal Rank Fusion + Cross-Encoder Reranker]
    M --> N{Pre-Generation Sufficiency Gate}
    N -->|Sufficient| O[Google Gemini 1.5 Flash Synthesis]
    N -->|Insufficient| P[Safe Refusal: Fact Not in Records]
    O --> Q{Post-Generation Fact-Check Gate}
    Q -->|Verified| R[Grounded Answer with Clickable Citations]
    Q -->|Low Grounding| S[Warning Flag Attached]
```

---

## 🛠️ Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, Zustand, Lucide Icons |
| **Backend** | FastAPI (Python 3.10+), Uvicorn, SQLAlchemy, Pydantic v2 |
| **Databases** | PostgreSQL / SQLite (Relational metadata), Qdrant Cloud (Vector DB) |
| **Storage & Auth** | Supabase Private Storage (HMAC Signed URLs), Firebase Authentication |
| **AI / NLP Models** | Google Gemini 1.5 Flash, BAAI/bge-m3, ms-marco-MiniLM-L-6-v2, EasyOCR, PyMuPDF |
| **Orchestration** | LangGraph (StateGraph multi-agent flow) |
| **Infrastructure** | Render (Web Services), Hugging Face Spaces (ZeroGPU NVIDIA A100) |

---

## 🚀 Getting Started

### 1. Prerequisites
* **Node.js:** v18.0 or higher
* **Python:** v3.10 or higher
* **Git**

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/healthvault-ai.git
cd healthvault-ai
```

---

### 3. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the root/backend directory:
```env
# Environment & Server
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000

# Database & Vector DB
DATABASE_URL="postgresql+psycopg://user:password@host:port/postgres?sslmode=require"
QDRANT_URL="https://your-cluster.qdrant.io:6333"
QDRANT_API_KEY="your-qdrant-api-key"

# AI / LLM Keys
GEMINI_API_KEY="your-google-gemini-api-key"
GEMINI_MODEL="gemini-1.5-flash"

# Supabase Storage (Private Bucket)
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_STORAGE_BUCKET="healthvault-medical-documents"
SUPABASE_SERVICE_ROLE_KEY="your-supabase-service-role-jwt-key"

# Firebase Auth
FIREBASE_PROJECT_ID="your-firebase-project-id"
FIREBASE_CLIENT_EMAIL="your-firebase-client-email"
FIREBASE_CREDENTIALS_PATH="serviceAccountKey.json"
```

Start the backend API server:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

---

### 4. Frontend Setup

```bash
# Open a new terminal and navigate to frontend
cd frontend

# Install Node dependencies
npm install
```

Create a `.env.local` file in the frontend folder:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_FIREBASE_API_KEY="your-firebase-api-key"
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN="your-app.firebaseapp.com"
NEXT_PUBLIC_FIREBASE_PROJECT_ID="your-project-id"
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET="your-app.firebasestorage.app"
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID="your-sender-id"
NEXT_PUBLIC_FIREBASE_APP_ID="your-app-id"
```

Start the Next.js development server:
```bash
npm run dev
```

Visit **`http://localhost:3000`** in your browser.

---

## 🔒 Security & Privacy Architecture

* **Tenant Isolation:** Every vector point and document chunk is tagged with an isolated `patient_id` filter in Qdrant and SQL queries.
* **Signed Medical Asset Access:** Files are never exposed via public URLs. Uploads to Supabase storage generate temporary, 5-minute HMAC-signed access tokens.
* **No PHI Training Retention:** Zero user data is used for model training or retained by third-party LLM providers.

---

## 🔮 Future Roadmap

- [ ] **Multilingual Support:** OCR and conversational QA in regional Indian languages (Hindi, Marathi, etc.).
- [ ] **Medication Adherence & Pill Tracker:** Automated reminders based on extracted dosage schedules.
- [ ] **Interactive Vitals Trend Graphing:** Dynamic charting for HbA1c, BP, and lipid profiles across time.
- [ ] **Drug-Drug Interaction Engine:** Cross-prescription warning alerts for contraindications.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
