# Zoro

A fitness and food-logging assistant that runs as an installable web app. Work in progress; see PLAN.md.

## Run it locally

Backend (Python 3.12+):

```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --env-file .env
```

Frontend (Node 20.19+ or 22.12+):

```
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173. The Today screen says whether it can reach the backend.
