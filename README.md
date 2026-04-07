# 🧠 AI Hackathon - AI-powered Banking FAQ Chatbot (React + FastAPI + MAAS Models)

A production-ready boilerplate built for Gen AI hackathons. Uses a Vite React frontend, FastAPI backend, and LangChain LLM integrations ready to connect to custom MAAS endpoints (like DeepSeek).

## 📁 Repository Structure
```
ai-friday-starterpack/
│── backend/                # FastAPI backend
│   ├── app/
│   │   ├── main.py         # Entry point and CORS
│   │   ├── routes/         # API Chat and Process routes
│   │   ├── services/       # LangChain MAAS LLM client logic
│   ├── requirements.txt
│   ├── .env.example
│── frontend/               # React + Vite frontend
│   ├── src/
│   │   ├── components/     # UI Components (InputBox, ResultCard, etc)
│   │   ├── pages/          # Home and Results views
│   │   ├── services/       # Axios API client
│   │   ├── App.jsx         # Router & Toast container
│   │   ├── index.css       # Tailwind base
│   ├── tailwind.config.js
```

---

## ▶️ Run Instructions (Step-by-step)

### 1. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Setup environment variables:
   Copy `.env.example` to `.env` and configure your API key.
   ```bash
   cp .env.example .env
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```
   *The backend will be running at `http://localhost:8000`. You can test the endpoints at `http://localhost:8000/docs`.*

---

### 2. Frontend Setup

1. Open a **new terminal tab** and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies (Node.js is required):
   ```bash
   npm install
   ```
3. Start the Vite React development server:
   ```bash
   npm run dev
   ```
   *The frontend will start quickly (usually at `http://localhost:5173` or similar).*

---

## 🔌 Integrating MAAS Models

The MAAS integration logic lives in `backend/app/services/llm_service.py` and `embedding_service.py`. It uses `httpx.Client(verify=False)` and a custom `base_url` to direct LangChain's standard OpenAI models to your internal MAAS platform.

If you change your internal URL or model name, update `MAAS_BASE_URL` and `model` fields inside these files.

## 🚀 Happy Hacking!
You now have a clean, extendable foundation to add complex logic into the `/process` API endpoint during your hackathon.


## Demo Video

[Show](Demo.mp4)