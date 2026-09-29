from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "phc_data.csv"
DATA.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ArogyaFlow AI", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

MEDICINES = ["Paracetamol", "ORS", "Amoxicillin", "Azithromycin", "IV Fluids"]

class SimulationRequest(BaseModel):
    outbreak: bool = True
    demand_multiplier: float = 1.35


def make_data():
    rng = np.random.default_rng(42)
    states = ["Telangana", "Andhra Pradesh", "Odisha"]
    districts = ["Hyderabad", "Warangal", "Visakhapatnam", "Guntur", "Koraput", "Cuttack"]
    rows = []
    for i in range(48):
        district = districts[i % len(districts)]
        state = states[districts.index(district) % len(states)]
        lat = 17.2 + (i % 8) * 0.28
        lon = 78.2 + (i % 6) * 0.42
        beds = int(rng.integers(12, 41))
        staff = int(rng.integers(4, 13))
        utilization = float(rng.uniform(0.35, 0.95))
        for medicine in MEDICINES:
            base = {"Paracetamol": 520, "ORS": 380, "Amoxicillin": 250, "Azithromycin": 190, "IV Fluids": 310}[medicine]
            demand = max(25, base * utilization + rng.normal(0, base * 0.08))
            stock_days = float(rng.uniform(2.0, 18.0))
            stock = int(demand * stock_days)
            rows.append({"phc_id": f"PHC-{i+1:03d}", "district": district, "state": state, "latitude": lat, "longitude": lon, "beds": beds, "staff": staff, "utilization": round(utilization, 3), "medicine": medicine, "stock": stock, "daily_demand": round(demand, 1), "stock_days": round(stock_days, 1)})
    return pd.DataFrame(rows)

if DATA.exists():
    df = pd.read_csv(DATA)
else:
    df = make_data()
    df.to_csv(DATA, index=False)


def analyze(multiplier=1.0):
    grouped = []
    for phc_id, g in df.groupby("phc_id"):
        demand = g["daily_demand"].sum() / len(g)
        weighted_stock_days = (g["stock_days"] * g["daily_demand"]).sum() / g["daily_demand"].sum()
        risk = min(99, max(4, (7 - weighted_stock_days) * 12 + (g["utilization"].iloc[0] - .5) * 35))
        if multiplier > 1:
            risk = min(99, risk + (multiplier - 1) * 42)
        grouped.append({
            "phc_id": phc_id, "district": g["district"].iloc[0], "state": g["state"].iloc[0],
            "latitude": g["latitude"].iloc[0], "longitude": g["longitude"].iloc[0],
            "beds": int(g["beds"].iloc[0]), "staff": int(g["staff"].iloc[0]),
            "utilization": round(float(g["utilization"].iloc[0]) * 100, 1),
            "avg_stock_days": round(float(weighted_stock_days), 1), "risk": round(float(risk), 1)
        })
    return pd.DataFrame(grouped)


def level(risk):
    return "Critical" if risk >= 75 else "High" if risk >= 50 else "Watch" if risk >= 30 else "Stable"

@app.get("/")
def root():
    return {"name": "ArogyaFlow AI", "status": "operational", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/summary")
def summary():
    a = analyze()
    return {
        "phcs": int(len(a)), "critical": int((a.risk >= 75).sum()), "high_risk": int(((a.risk >= 50) & (a.risk < 75)).sum()),
        "avg_utilization": round(float(a.utilization.mean()), 1), "beds_available": int((df["beds"] * (1-df["utilization"])).groupby(df["phc_id"]).first().sum()),
        "last_updated": "Live simulation"
    }

@app.get("/api/phcs")
def phcs():
    a = analyze()
    records = a.to_dict(orient="records")
    for x in records: x["status"] = level(x["risk"])
    return records

@app.get("/api/medicines")
def medicines():
    out = []
    for med, g in df.groupby("medicine"):
        stock = int(g.stock.sum())
        daily = float(g.daily_demand.sum())
        days = stock / max(daily, 1)
        risk = min(99, max(3, (7 - days) * 14))
        forecast = daily * 7
        out.append({"medicine": med, "stock": stock, "daily_demand": round(daily,1), "days_cover": round(days,1), "forecast_7d": round(forecast,0), "risk": round(risk,1), "status": level(risk)})
    return out

@app.get("/api/forecast/{phc_id}")
def forecast(phc_id: str, medicine: Optional[str] = "Paracetamol"):
    g = df[(df.phc_id == phc_id) & (df.medicine == medicine)]
    if g.empty: return {"error": "PHC or medicine not found"}
    base = float(g.daily_demand.iloc[0])
    history = [round(max(10, base * (0.82 + i*0.025) + np.sin(i)*base*.04), 1) for i in range(14)]
    x = np.arange(len(history)).reshape(-1,1)
    model = LinearRegression().fit(x, np.array(history))
    future_x = np.arange(14,21).reshape(-1,1)
    pred = model.predict(future_x).clip(min=0)
    return {"phc_id": phc_id, "medicine": medicine, "history": history, "forecast": [round(float(v),1) for v in pred], "model": "Linear trend + operational risk engine"}

@app.post("/api/simulate")
def simulate(req: SimulationRequest):
    a = analyze(req.demand_multiplier if req.outbreak else 1.0)
    critical = a[a.risk >= 75].sort_values("risk", ascending=False).head(8)
    return {"outbreak": req.outbreak, "demand_multiplier": req.demand_multiplier, "critical_phcs": [{**x, "status": level(x["risk"])} for x in critical.to_dict(orient="records")], "critical_count": int((a.risk >= 75).sum())}

@app.get("/api/recommendations")
def recommendations():
    a = analyze().sort_values("risk", ascending=False)
    donors = a[a.risk < 30].head(6).reset_index(drop=True)
    receivers = a[a.risk >= 60].head(6).reset_index(drop=True)
    recs = []
    for i, r in receivers.iterrows():
        d = donors.iloc[i % len(donors)] if len(donors) else None
        if d is not None:
            qty = int(250 + (r.risk - 60) * 12)
            recs.append({"from_phc": d.phc_id, "from_district": d.district, "to_phc": r.phc_id, "to_district": r.district, "medicine": MEDICINES[i % len(MEDICINES)], "quantity": qty, "priority": "Urgent" if r.risk >= 75 else "High", "reason": f"{r.phc_id} has {r.avg_stock_days} days of cover and {r.risk}% predicted risk."})
    return recs
