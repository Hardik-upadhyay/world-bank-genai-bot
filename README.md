# 🏦 World Bank AI Banking Assistant

> **Version:** 2.0.0 | **Stack:** FastAPI + React (Vite) | **AI Provider:** TCS MaaS (Azure-hosted)

A production-ready, full-stack AI chatbot that answers real banking questions in real time — accurately, instantly, and in any language. Built for **TCS AI Fridays Season 2** hackathon.

---

## ✨ Features

- 🤖 **5-Model AI Orchestration** — DeepSeek-V3 as primary, with automatic fallback chain through GPT-4o → GPT-4o-mini → GPT-3.5-Turbo for 100% uptime reliability
- 📚 **RAG Pipeline** — Retrieval-Augmented Generation using ChromaDB + `text-embedding-3-large` (3072-dim vectors) to ground every answer in actual banking policy documents
- 🌍 **Multi-language Support** — Auto-detects user language, translates query to English internally, and responds in the user's language
- 🔐 **JWT Authentication** — Secure login with role-based access (Customer / Manager)
- 👤 **Live Customer Context** — For authenticated users, pulls real-time account balances, transaction history, and loan data from SQLite
- 🖼️ **Vision Support** — GPT-4o analyzes uploaded bank statements, cheques, and screenshots
- 📊 **Manager Dashboard** — Admin panel for customer management and oversight
- 💬 **Chat History** — Persistent session management with full conversation history
- ⚡ **Sub-3-second response time** | **85%+ accuracy target**

---

## 📁 Repository Structure

```
ai-friday-starterpack/
│── backend/                        # FastAPI backend
│   ├── app/
│   │   ├── main.py                 # Entry point and CORS
│   │   ├── routes/
│   │   │   ├── process.py          # Main AI chat endpoint (/process)
│   │   │   ├── chat.py             # Direct chat + translation
│   │   │   ├── auth.py             # JWT authentication
│   │   │   ├── customer.py         # Customer dashboard
│   │   │   ├── manager.py          # Manager/admin routes
│   │   │   └── history.py          # Chat session management
│   │   ├── services/
│   │   │   ├── llm_service.py      # 5-model orchestrator (DeepSeek + GPT fallback chain)
│   │   │   ├── rag_service.py      # ChromaDB retrieval + embedding search
│   │   │   └── embedding_service.py # text-embedding-3-large vector generation
│   ├── requirements.txt
│   ├── .env.example
│── frontend/                       # React + Vite frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatMessage.jsx     # Markdown rendering + model badge + export CSV/PDF + translate
│   │   │   ├── InputBox.jsx        # Text input + file upload
│   │   │   ├── SourceCitations.jsx # RAG source display
│   │   │   ├── ChatPdfDocument.jsx # PDF export template
│   │   │   └── ThinkingIndicator.jsx # Loading animation
│   │   ├── pages/
│   │   │   ├── Landing.jsx         # Public FAQ + unauthenticated chat
│   │   │   ├── Login.jsx           # JWT auth form
│   │   │   ├── Home.jsx            # Dual-pane: Dashboard + Chat
│   │   │   └── ManagerDashboard.jsx # Customer management
│   │   ├── services/
│   │   │   ├── api.js              # Axios + auto JWT injection
│   │   │   └── auth.js             # LocalStorage token management
│   │   ├── App.jsx                 # Router & Toast container
│   │   └── index.css               # Tailwind base
│   ├── tailwind.config.js
```

---

## 🧠 AI Models Used

All models are hosted on **TCS MaaS** (Model-as-a-Service) at `https://genailab.tcs.in` via the OpenAI-compatible API.

| # | Model | Role |
|---|-------|------|
| 1 | **DeepSeek-V3-0324** | Primary conversational AI — handles all chat requests first |
| 2 | **DeepSeek-R1** | Available for deep analytical reasoning via `call_reasoning_model()` |
| 3 | **GPT-4o** | Fallback #1 + Vision analysis (bank statements, cheques, images) |
| 4 | **GPT-4o-mini** | Fallback #2 — lightweight, low-latency fallback |
| 5 | **GPT-3.5-Turbo** | Fallback #3 — last-resort to guarantee service continuity |
| 6 | **text-embedding-3-large** | 3072-dim embeddings for RAG semantic search (ChromaDB) |

---

## 🔄 The 5-Step AI Pipeline

Every chat request goes through this pipeline:

```
User Query
    │
    ▼
[1] LANGUAGE DETECTION  ←  GPT fallback chain → detects language + translates to English
    │
    ▼
[2] QUERY ROUTING       ←  Rule-based: personal | general | guest-deflect
    │
    ▼
[3] DATA ENRICHMENT     ←  SQLite (customer data) + ChromaDB similarity search
    │                       text-embedding-3-large → top-5 relevant FAQ chunks
    ▼
[4] PROMPT ASSEMBLY     ←  System Prompt + Customer Context + RAG Context + User Question
    │
    ▼
[5] LLM GENERATION      ←  DeepSeek-V3 → GPT-4o → GPT-4o-mini → GPT-3.5 (fallback chain)
    │
    ▼
BankingChatResponse {answer, sources, model_used, detected_language, query_type}
```

---

## 🗺️ API Route Map

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/process` | Optional JWT | **Main AI chat endpoint** |
| `POST` | `/process/upload` | Required JWT | Image/PDF file analysis |
| `POST` | `/chat` | None | Simple raw chat |
| `POST` | `/chat/translate` | None | Real-time message translation |
| `POST` | `/auth/login` | None | User authentication (JWT issued) |
| `GET` | `/customer/dashboard` | JWT (customer) | Account data from SQLite |
| `GET/POST` | `/manager/customers` | JWT (manager) | Customer management |
| `POST` | `/history/sessions` | JWT | Create chat session |
| `GET` | `/history/sessions` | JWT | List user's sessions |
| `GET/PUT/DELETE` | `/history/sessions/{id}` | JWT | Manage individual sessions |
| `GET` | `/public` | None | Health check |

---

## ▶️ Run Instructions

### Prerequisites

- Python 3.9+
- Node.js 18+
- MaaS API access (`https://genai.company.in`)

---

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your TCS MaaS API key and base URL

# Run the FastAPI server
uvicorn app.main:app --reload
```

> Backend runs at `http://localhost:8000` — Swagger docs at `http://localhost:8000/docs`

---

### 2. Frontend Setup

```bash
# Open a new terminal tab and navigate to frontend
cd frontend

# Install dependencies
npm install

# Start the Vite dev server
npm run dev
```

> Frontend runs at `http://localhost:5173`

---

## 🔌 Configuring TCS MaaS Models

The MaaS integration lives in `backend/app/services/llm_service.py` and `embedding_service.py`.

Key environment variables to set in `.env`:

```env
MAAS_BASE_URL=https://genailab.tcs.in
MAAS_API_KEY=your_api_key_here
```

To swap models or update the base URL, modify `MAAS_BASE_URL` and the `model` identifiers inside `llm_service.py`.

---

## 🗄️ Data Layer

- **ChromaDB** — Vector store for banking FAQ documents (`banking_faq` collection)
- **SQLite** (`world_bank.db`) — Stores customers, accounts, transactions, and chat sessions

To seed the vector store with FAQ documents, run:

```bash
python app/db_seeder.py
```

---

## 🎬 Demo Video

[Watch Demo](Demo.mp4)

---

## 🏆 Built at TCS AI Fridays Season 2 — First Place 🥇
