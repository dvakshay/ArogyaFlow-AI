# ArogyaFlow AI

AI-powered health resource resilience platform for Primary Health Centres (PHCs).

## Problem
Public healthcare networks can face medicine stock-outs, uneven resource utilization, and delayed response during health emergencies.

## Solution
ArogyaFlow AI provides a national operations dashboard that monitors PHC readiness, forecasts medicine demand, detects stock-out risk, simulates emergency demand shocks, and recommends cross-district resource redistribution.

## MVP capabilities
- PHC operational risk scoring
- Medicine stock and days-of-cover monitoring
- Lightweight demand forecasting using historical demand trends
- Emergency outbreak simulation (+35% demand scenario)
- AI-assisted redistribution recommendations
- National-level operational dashboard

## Architecture
React + Vite frontend → FastAPI backend → Python prediction/recommendation engine → CSV-backed MVP dataset.

## Run locally
### Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173  
API: http://127.0.0.1:8000

## Note
The MVP uses synthetic operational data for demonstration. A production implementation would connect to authenticated national health data systems, live inventory systems, facility registries, and emergency surveillance feeds.
