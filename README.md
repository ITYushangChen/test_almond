# COMP9900 – Corporate Culture Monitor

A full-stack analytics app for employee sentiment, themes and benchmarks. Includes a Flask backend (Supabase), React frontend, and data-pre utilities for offline evaluation/visualization.

## 1) Prerequisites
- Node.js 18+
- Python 3.10+
- Docker (optional but recommended)

## 2) Quick Start (Docker – recommended)
1. Copy environment files (fill in your own values):
   - `cp backend/.env.example backend/.env`
   - `cp frontend/.env.example frontend/.env`
   - `cp data-pre/.env.example data-pre/.env` (optional, for data-pre scripts)
2. Start services:
   - `docker-compose up --build`
3. Access:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5050

Notes:
- Backend connects to Supabase using `SUPABASE_URL` and `SUPABASE_KEY` from `backend/.env`.
- OpenAI features are optional; set `OPENAI_API_KEY` if you want AI insights/models.

## 3) Manual Start (without Docker)
### Backend (Flask)
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill SUPABASE_URL, SUPABASE_KEY, etc.
python app.py          # serves on http://localhost:5000 (proxied as 5050 in Docker)
```

### Frontend (React)
```bash
cd frontend
npm install
cp .env.example .env   # set REACT_APP_API_URL (default http://localhost:5050)
npm start              # http://localhost:3000
```

## 4) Environment Variables
### backend/.env
```env
SUPABASE_URL= https://your-project.supabase.co
SUPABASE_KEY= your-anon-or-service-role-key
JWT_SECRET_KEY= change-this-secret
OPENAI_API_KEY=           # optional
OPENAI_MODEL= gpt-4o      # optional
```

### frontend/.env
```env
REACT_APP_API_URL= http://localhost:5050
```

### data-pre/.env (optional for scripts)
```env
SUPABASE_URL= https://your-project.supabase.co
SUPABASE_KEY= your-anon-or-service-role-key
OPENAI_API_KEY=
```

## 5) Project Structure (key paths)
```
backend/                 # Flask API (Supabase)
frontend/                # React app (Recharts, Theme, etc.)
data-pre/                # Offline scripts (sampling, model eval, visualization)
  sentiment_analysis/
    run_comparison.py    # compare models (uses sentiment_test_set.json)
    visualize_results.py # generate charts (pngs)
  sentiment_test_set.json# generated locally; git-ignored
```

## 6) Data-pre Usage (optional)
Generate a test set (50 samples) and compare models:
```bash
cd data-pre
# ensure .env exists if sampling from Supabase
python3 -m sentiment_analysis.run_comparison        # if test set exists
python3 -m sentiment_analysis.visualize_results     # writes pngs to sentiment_analysis/
```
If you want to build your own test set from Supabase, adapt or restore the sampling script.

## 7) Git Hygiene
- Real secrets `.env` are git-ignored
- Example files `*.env.example` are committed for easy onboarding
- Generated images and test sets under `data-pre` are ignored

## 8) Troubleshooting
- Frontend cannot reach backend: verify `REACT_APP_API_URL` and backend is running on 5050/5000
- Supabase auth/queries failing: re-check `SUPABASE_URL` and `SUPABASE_KEY`
- AI features not working: set `OPENAI_API_KEY` in `backend/.env` (and restart)

## 9) License
Internal/Academic use. Update as needed.
