╔══════════════════════════════════════════════════════════════════════╗
║                    HEALTHVAULT AI — PERSON 3                       ║
║              RAG + RETRIEVAL + REASONING ENGINE                    ║
╚══════════════════════════════════════════════════════════════════════╝


                    ┌─────────────────────────┐
                    │      PERSON 2           │
                    │  OCR + NLP Pipeline     │
                    └────────────┬────────────┘
                                 │
                                 │ Structured Medical Records
                                 │
                                 ▼
╔══════════════════════════════════════════════════════════════════════╗
║                         PHASE 1: INDEXING                           ║
╚══════════════════════════════════════════════════════════════════════╝

                    Structured Medical Record
                              │
                              ▼
                    ┌───────────────────┐
                    │ Format Record     │
                    │ + Prepare Text    │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ Record-Based      │
                    │ Chunking          │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │     BGE-M3        │
                    │ Embedding Model   │
                    └─────────┬─────────┘
                              │
                              ▼
                       Vector Embedding
                         [1024 values]
                              │
                              ▼
                    ┌───────────────────┐
                    │      QDRANT       │
                    │   Vector Store    │
                    ├───────────────────┤
                    │ Vector            │
                    │ + patient_id      │
                    │ + document_id     │
                    │ + visit_id        │
                    │ + date            │
                    │ + confidence      │
                    │ + needs_review    │
                    └───────────────────┘


                 ↑ KNOWLEDGE BASE IS NOW INDEXED ↑


╔══════════════════════════════════════════════════════════════════════╗
║                    PHASE 2: DOCTOR QUERY                            ║
╚══════════════════════════════════════════════════════════════════════╝

                         Doctor's Question
                               │
                               ▼
                 "What was P001's latest HbA1c?"
                               │
                               ▼
                    ┌───────────────────┐
                    │  Patient ID       │
                    │  = P001           │
                    └─────────┬─────────┘
                              │
                              ▼
                   PATIENT-SCOPED SEARCH
                              │
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
       ┌─────────────────┐         ┌─────────────────┐
       │   DENSE SEARCH  │         │   BM25 SEARCH   │
       │                 │         │                 │
       │ Question →      │         │ Keyword /       │
       │ BGE-M3 vector   │         │ exact-term      │
       │                 │         │ matching        │
       │ Semantic        │         │                 │
       │ similarity      │         │ Sparse search   │
       └────────┬────────┘         └────────┬────────┘
                │                           │
                │                           │
                └─────────────┬─────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │       RRF         │
                    │ Reciprocal Rank   │
                    │      Fusion       │
                    │                   │
                    │ Combines Dense +  │
                    │ BM25 rankings     │
                    └─────────┬─────────┘
                              │
                              ▼
                     Top ~15 Candidates
                              │
                              ▼
                    ┌───────────────────┐
                    │   CROSS-ENCODER   │
                    │                   │
                    │ Question +        │
                    │ Document together │
                    │                   │
                    │ Relevance Score   │
                    └─────────┬─────────┘
                              │
                              ▼
                       Top 3–5 Records
                              │
                              ▼


╔══════════════════════════════════════════════════════════════════════╗
║                 PHASE 3: EVIDENCE SAFETY GATE                      ║
╚══════════════════════════════════════════════════════════════════════╝

                    Retrieved Evidence
                              │
                              ▼
                 ┌────────────────────────┐
                 │ Evidence Sufficiency   │
                 │        Check           │
                 │                        │
                 │ Does the retrieved     │
                 │ evidence actually      │
                 │ contain the requested  │
                 │ medical information?   │
                 └───────────┬────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                   NO                YES
                    │                 │
                    ▼                 ▼
             ┌─────────────┐   ╔══════════════════════╗
             │   ABSTAIN   │   ║  PHASE 4: LANGGRAPH ║
             │             │   ╚══════════════════════╝
             │ "No relevant│                 │
             │ information │                 │
             │ was found..."                │
             └─────────────┘                 ▼


╔══════════════════════════════════════════════════════════════════════╗
║                    PHASE 4: LANGGRAPH                              ║
║                   REASONING WORKFLOW                               ║
╚══════════════════════════════════════════════════════════════════════╝

                         Valid Query
                              │
                              ▼
                    ┌───────────────────┐
                    │    ROUTER NODE    │
                    │                   │
                    │ What type of      │
                    │ question is this? │
                    └─────────┬─────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
             SIMPLE LOOKUP       COMPLEX REASONING
                    │                   │
                    │                   ▼
                    │          ┌──────────────────┐
                    │          │ RETRIEVAL NODE   │
                    │          └────────┬─────────┘
                    │                   │
                    │                   ▼
                    │          ┌──────────────────┐
                    │          │  TIMELINE NODE   │
                    │          │                  │
                    │          │ Orders medical   │
                    │          │ events across    │
                    │          │ visits/dates     │
                    │          └────────┬─────────┘
                    │                   │
                    │                   ▼
                    │          ┌──────────────────┐
                    │          │ CONSISTENCY NODE │
                    │          │                  │
                    │          │ Detects changes  │
                    │          │ / conflicts in   │
                    │          │ records          │
                    │          └────────┬─────────┘
                    │                   │
                    └─────────┬─────────┘
                              │
                              ▼


╔══════════════════════════════════════════════════════════════════════╗
║                    PHASE 5: SYNTHESIS                              ║
╚══════════════════════════════════════════════════════════════════════╝

                    ┌─────────────────────┐
                    │   SYNTHESIS NODE    │
                    │                     │
                    │ Combines:           │
                    │                     │
                    │ • User question     │
                    │ • Retrieved docs    │
                    │ • Timeline          │
                    │ • Consistency info  │
                    │ • Confidence data   │
                    └──────────┬──────────┘
                               │
                               ▼
                         ┌───────────┐
                         │    LLM    │
                         │           │
                         │ Generates │
                         │ grounded │
                         │ answer    │
                         └─────┬─────┘
                               │
                               ▼
                       Generated Answer
                               │
                               ▼


╔══════════════════════════════════════════════════════════════════════╗
║                   PHASE 6: CITATION VALIDATION                     ║
╚══════════════════════════════════════════════════════════════════════╝

                         Generated Answer
                               │
                               ▼
                  ┌────────────────────────┐
                  │ CITATION VALIDATOR     │
                  │                        │
                  │ Check:                 │
                  │ • Document exists?     │
                  │ • Citation retrieved?  │
                  │ • Claim supported?     │
                  │ • No unsupported      │
                  │   medical claims?      │
                  └───────────┬────────────┘
                              │
                       ┌──────┴──────┐
                       │             │
                     VALID        INVALID
                       │             │
                       ▼             ▼
                  ┌─────────┐   ┌───────────┐
                  │ FINAL   │   │ Reject /  │
                  │ ANSWER  │   │ Rework /  │
                  │         │   │ Flag      │
                  └────┬────┘   └───────────┘
                       │
                       ▼
╔══════════════════════════════════════════════════════════════════════╗
║                         FINAL ANSWER                                ║
║                                                                    ║
║ P001's latest recorded HbA1c was 8.1% on July 15, 2026.           ║
║                                                                    ║
║ Source: DOC002 — 2026-07-15                                       ║
╚══════════════════════════════════════════════════════════════════════╝