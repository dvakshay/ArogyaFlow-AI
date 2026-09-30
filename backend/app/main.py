from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.intelligence import (
    build_phc_intelligence,
    find_stockout_risks,
    forecast_demand,
    generate_redistribution_recommendations,
)


BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "phc_data.csv"


MEDICINES = [
    "Paracetamol",
    "ORS",
    "Amoxicillin",
    "Azithromycin",
    "IV Fluids",
]


app = FastAPI(
    title="ArogyaFlow AI",
    description="Predictive health-resource resilience platform for PHCs.",
    version="1.2.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


df = pd.read_csv(DATA)


class SimulationRequest(BaseModel):
    outbreak: bool = True
    demand_multiplier: float = 1.35


@app.get("/")
def root():
    return {
        "name": "ArogyaFlow AI",
        "version": "1.2.0",
        "status": "operational",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "ArogyaFlow AI",
        "records": len(df),
    }


@app.get("/api/summary")
def summary():
    intelligence = build_phc_intelligence(df)

    risks = [
        float(item.get("risk", 0))
        for item in intelligence
    ]

    total_phcs = len(intelligence)

    critical = sum(
        risk >= 75
        for risk in risks
    )

    high_risk = sum(
        50 <= risk < 75
        for risk in risks
    )

    watch = sum(
        25 <= risk < 50
        for risk in risks
    )

    stable = sum(
        risk < 25
        for risk in risks
    )

    utilizations = [
        float(item.get("utilization", 0))
        for item in intelligence
        if item.get("utilization") is not None
    ]

    beds = [
        float(item.get("beds", 0))
        for item in intelligence
        if item.get("beds") is not None
    ]

    avg_utilization = (
        sum(utilizations) / len(utilizations)
        if utilizations
        else 0
    )

    total_beds = sum(beds)

    beds_available = sum(
        beds[i] * (
            1 - utilizations[i] / 100
        )
        for i in range(
            min(len(beds), len(utilizations))
        )
    ) if beds and utilizations else 0

    return {
        # Frontend-compatible fields
        "phcs": total_phcs,
        "critical": critical,
        "high_risk": high_risk,
        "watch": watch,
        "stable": stable,
        "avg_utilization": round(
            avg_utilization,
            1,
        ),
        "beds_available": round(
            beds_available
        ),

        # Additional backend intelligence
        "total_phcs": total_phcs,
        "critical_phcs": critical,
        "high_risk_phcs": high_risk,
        "stable_phcs": stable,
        "average_risk": round(
            sum(risks) / len(risks),
            2,
        ) if risks else 0,
        "total_beds": round(
            total_beds
        ),
        "medicines": MEDICINES,
    }


@app.get("/api/phcs")
def phcs():
    return build_phc_intelligence(df)


@app.get("/api/intelligence")
def intelligence():
    return build_phc_intelligence(df)


@app.get("/api/medicines")
def medicines():
    stockouts = find_stockout_risks(
        df,
        demand_multiplier=1.0,
    )

    result = []

    for medicine in MEDICINES:
        medicine_df = df[
            df["medicine"] == medicine
        ]

        if medicine_df.empty:
            continue

        total_stock = float(
            medicine_df["stock"].sum()
        )

        total_daily_demand = float(
            medicine_df["daily_demand"].sum()
        )

        days_cover = (
            total_stock / total_daily_demand
            if total_daily_demand > 0
            else 0
        )

        seven_day_demand = (
            total_daily_demand * 7
        )

        medicine_risks = [
            item
            for item in stockouts
            if item["medicine"] == medicine
        ]

        highest_risk = (
            max(
                item["risk"]
                for item in medicine_risks
            )
            if medicine_risks
            else 0
        )

        status = (
            "Critical"
            if highest_risk >= 75
            else "Watch"
            if highest_risk >= 50
            else "Stable"
        )

        result.append(
            {
                "medicine": medicine,

                # Frontend-compatible fields
                "stock": round(
                    total_stock,
                    1,
                ),

                "daily_demand": round(
                    total_daily_demand,
                    1,
                ),

                "days_cover": round(
                    days_cover,
                    1,
                ),

                "forecast_7d": round(
                    seven_day_demand,
                    1,
                ),

                "risk": round(
                    highest_risk,
                    1,
                ),

                "status": status,

                # Backend-friendly alias
                "total_stock": round(
                    total_stock,
                    1,
                ),
            }
        )

    return result

@app.get("/api/stockouts")
def stockouts():
    return find_stockout_risks(
        df,
        demand_multiplier=1.0,
    )


@app.get("/api/forecast/{phc_id}")
def phc_forecast(phc_id: str):
    phc_df = df[df["phc_id"] == phc_id]

    if phc_df.empty:
        return {
            "phc_id": phc_id,
            "forecast": [],
            "message": "PHC not found",
        }

    base_daily_demand = float(
        phc_df["daily_demand"].sum()
    )

    forecast = forecast_demand(
        base_daily_demand
    )

    return {
        "phc_id": phc_id,
        **forecast,
    }


@app.post("/api/simulate")
def simulate(req: SimulationRequest):
    multiplier = (
        req.demand_multiplier
        if req.outbreak
        else 1.0
    )

    intelligence = build_phc_intelligence(
        df,
        demand_multiplier=multiplier,
    )

    stockouts = find_stockout_risks(
        df,
        demand_multiplier=multiplier,
    )

    # Medicine-level critical pressure
    critical_stockouts = [
        item
        for item in stockouts
        if item["risk"] >= 75
    ]

    # PHCs affected by at least one critical medicine shortage
    affected_phc_ids = {
        item["phc_id"]
        for item in critical_stockouts
    }

    # Combine operational PHC risk + medicine shortage risk
    phc_map = {}

    for item in intelligence:
        phc_id = item["phc_id"]

        phc_map[phc_id] = {
            "phc_id": phc_id,
            "district": item.get("district"),
            "state": item.get("state"),
            "risk": item.get("risk", 0),
            "status": item.get("status"),
            "critical_medicines": [],
        }

    for item in critical_stockouts:
        phc_id = item["phc_id"]

        if phc_id not in phc_map:
            phc_map[phc_id] = {
                "phc_id": phc_id,
                "district": item.get("district"),
                "state": item.get("state"),
                "risk": 0,
                "status": "Critical",
                "critical_medicines": [],
            }

        phc_map[phc_id]["critical_medicines"].append(
            {
                "medicine": item["medicine"],
                "risk": item["risk"],
                "days_cover": item["days_cover"],
                "shortage": item["shortage"],
            }
        )

        # Medicine shortage should elevate emergency PHC risk
        phc_map[phc_id]["risk"] = max(
            phc_map[phc_id]["risk"],
            item["risk"],
        )

        phc_map[phc_id]["status"] = (
            "Critical"
            if item["risk"] >= 75
            else phc_map[phc_id]["status"]
        )

    critical_phcs = sorted(
        [
            item
            for item in phc_map.values()
            if item["phc_id"] in affected_phc_ids
        ],
        key=lambda item: item["risk"],
        reverse=True,
    )[:10]

    emergency_recommendations = (
        generate_redistribution_recommendations(
            df=df,
            demand_multiplier=multiplier,
        )
    )

    return {
        "outbreak": req.outbreak,
        "demand_multiplier": multiplier,

        "critical_count": len(affected_phc_ids),

        "critical_stockout_count": len(
            critical_stockouts
        ),

        "critical_phcs": critical_phcs,

        "stockout_risks": stockouts[:15],

        "redistribution_actions": len(
            emergency_recommendations
        ),

        "emergency_recommendations": (
            emergency_recommendations[:10]
        ),

        "message": (
            "Emergency demand simulation completed. "
            "Critical medicine shortages were identified "
            "and AI redistribution actions were generated."
        ),
    }


@app.get("/api/recommendations")
def recommendations():
    return generate_redistribution_recommendations(
        df=df,
        demand_multiplier=1.0,
    )