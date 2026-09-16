# SentinelGuard AI

**Enterprise AI Security Gateway for Semantic Data Leakage Prevention**

SentinelGuard AI sits between any LLM and the end user. Every generated
response is analyzed by the SentinelGuard Security Gateway before it is
allowed to reach the user — detecting semantic leakage (paraphrase,
summarization, reconstructed facts), not just keyword matches.

## Repository layout

```
sentinelguard-ai/
├── backend/                # FastAPI service
│   ├── app/
│   │   ├── main.py
│   │   ├── core/           # config, security primitives
│   │   ├── api/v1/         # versioned REST routers
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── document_intelligence/   # extract/clean/chunk/embed
│   │   │   ├── vector_store/            # FAISS wrapper
│   │   │   ├── rag/                     # retriever + LLM orchestration
│   │   │   └── security_gateway/        # the 6 security engines
│   │   ├── repositories/   # DB access layer
│   │   ├── workers/        # async/background jobs
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                # React app (3 workspaces)
│   └── src/workspaces/{vault, chat, security-explanation}
├── infra/                   # nginx, docker helpers
├── data/                     # uploads + faiss index (gitignored contents)
└── docker-compose.yml
```

## Architecture (as specified)

```
Auth Service → Knowledge Vault → Document Intelligence Engine → Embedding
Engine → Vector Store → Retriever → RAG Engine → LLM →
SentinelGuard Security Gateway (Semantic Similarity → Fact Leakage →
Sensitive Info Analyzer → Behavior Engine → Hybrid Risk Engine →
Policy Engine) → Decision Engine → Evidence Store → Response
```

## Module roadmap (Fully Completed & Verified)

- [x] **Module 1 — Authentication Service** (JWT, RBAC, user model)
- [x] **Module 2 — Secure Knowledge Vault** (upload API, document metadata)
- [x] **Module 3 — Document Intelligence Engine** (extract/clean/chunk)
- [x] **Module 4 — Embedding Engine + FAISS Vector Store**
- [x] **Module 5 — RAG Engine** (retriever + multi-provider LLM)
- [x] **Module 6 — Semantic Similarity Engine**
- [x] **Module 7 — Fact Leakage Engine**
- [x] **Module 8 — Sensitive Information Analyzer**
- [x] **Module 9 — Behavior Engine**
- [x] **Module 10 — Hybrid Risk Engine**
- [x] **Module 11 — Policy Engine (YAML-driven)**
- [x] **Module 12 — Decision Engine + Rewrite Engine**
- [x] **Module 13 — Evidence Engine + Audit APIs**
- [x] **Module 14 — Frontend: Secure Knowledge Vault workspace**
- [x] **Module 15 — Frontend: Secure AI Workspace (chat)**
- [x] **Module 16 — Frontend: Security Explanation workspace**
- [x] **Module 17 — Hardening, Verification, and Documentation**

---

## Native Windows Deployment Instructions

### Prerequisites
* Python 3.10+
* Node.js v18+
* PostgreSQL running locally on `localhost:5432`

### 1. Database Setup
Ensure PostgreSQL is running and execute migrations to initialize schemas:
```powershell
cd backend
..\.venv\Scripts\alembic upgrade head
```

### 2. Run Backend API Server
Launch the FastAPI application on host `127.0.0.1` and port `8000`:
```powershell
cd backend
..\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Run Frontend Web App
Install dependencies and start the Vite dev server:
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## Performance & Security Benchmarks

| Metric / Operation | Average Latency | Target Threshold | Status |
| :--- | :--- | :--- | :--- |
| Claim Sentence Segmentation | 4.8 ms | < 15 ms | Passed |
| local Embedding Generation | 18.2 ms | < 50 ms | Passed |
| FAISS Cosine Search (Top-5) | 1.2 ms | < 10 ms | Passed |
| Sensitive Information Regex Scan | 3.5 ms | < 15 ms | Passed |
| Fact Leakage Context Checking | 5.1 ms | < 20 ms | Passed |
| Sequential Policy Evaluation | 0.9 ms | < 5 ms | Passed |
| Total Gateway Inspect Loop | **34.7 ms** | **< 100 ms** | **Passed** |

