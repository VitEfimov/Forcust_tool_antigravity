---
description: Run the Antigravity application (Backend + Frontend)
---

To run the application, you need to start both the backend and the frontend.

1. Start the Backend (FastAPI)

Option A - With pip:
```bash
// turbo
pip install -r requirements.txt
// turbo
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Option B - With poetry (if installed):
```bash
// turbo
poetry install
// turbo
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

2. Start the Frontend (React) - Open a new terminal for this
```bash
cd frontend
// turbo
npm install
// turbo
npm run dev
```
