---
title: HealthVault AI BGE-M3 Embedder
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# HealthVault AI Cloud Microservice

High-performance AI microservice hosting **`BAAI/bge-m3`** (1024-dimensional dense vectors), Medical NER entity extraction, and clinical text processing for **HealthVault Medical Locker**.

### Endpoints:
- `GET /`: Health check & active device status
- `POST /embed`: Generates 1024-d dense embeddings for medical text chunks & RAG search queries
- `POST /process-text`: Extracts structured clinical entities (medications, dosages, lab tests, diagnoses)
