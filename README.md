# Afyamama - AI Maternal & Child Health Tracker (MVP)

**System by Simon**

This repository contains a minimal, deployable MVP for *Afyamama* — a maternal & child health risk tracker.
The project is purposely built to run without paid APIs and to be deployed using Streamlit for the frontend and (optionally) Render for a backend FastAPI service.

## What's included
- `frontend/streamlit_app.py` — Main Streamlit app (forms, profiles, risk assessment, AI assistant).
- `frontend/db.py` — Simple SQLite helper for storing mothers, children, and chat logs.
- `frontend/risk_model.py` — A simple rule-based risk predictor (upgradeable to ML).
- `frontend/ai_assistant.py` — Rule-based AI assistant logic supporting English/Swahili responses.
- `backend/app.py` — Optional FastAPI backend (example endpoints).
- `requirements.txt` — Python dependencies.

## How to run (local)
1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Run the Streamlit frontend:
   ```bash
   streamlit run frontend/streamlit_app.py
   ```
   The app will create a SQLite database file at `frontend/afyamama.db`.

3. (Optional) Run backend:
   ```bash
   uvicorn backend.app:app --reload --port 8000
   ```
   The Streamlit frontend currently works standalone (it reads/writes SQLite) but the backend is provided if you want to move logic server-side.

## Notes
- The AI assistant is rule-based for offline/free operation (no API keys).
- The footer contains the text: **System by Simon**
- You can edit files under `frontend/` to customize responses, add more rules, or integrate a small HuggingFace model later.

## File map
```
afyamama_project/
├─ frontend/
│  ├─ streamlit_app.py
│  ├─ db.py
│  ├─ risk_model.py
│  └─ ai_assistant.py
├─ backend/
│  └─ app.py
├─ requirements.txt
└─ README.md
```
