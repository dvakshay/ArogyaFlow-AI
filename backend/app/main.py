from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.intelligence import (
    build_phc_intelligence,
    find_stockout_risks,
    forecast_demand,
    generate_redistribution_recommendations,
    risk_level,
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
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulationRequest(BaseModel):
    outbreak: bool = True
    demand_multiplier: float = 1.35


if DATA.exists():
    df = pd.read_csv(DATA)
else:
    raise FileNotFoundError(
        f"PHC dataset not found at {DATA}"
    )


@app.get("/")
def root():
    return {
        "name": "ArogyaFlow AI",
        "status": "operational",
        "version": "1.1.0",
        "description": "Predictive PHC health-resource resilience platform",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "arogyaflow-backend",
    }


@app.get("/api/summary")
def summary():

    intelligence = pd.DataFrame(
        build_phc_intelligence(df)
    )

    return {
        "phcs": int(len(intelligence)),
        "critical": int(
            (intelligence["risk"] >= 75).sum()
        ),
        "high_risk": int(
            (
                (intelligence["risk"] >= 50)
                & (intelligence["risk"] < 75)
            ).sum()
        ),
        "watch": int(
            (
                (intelligence["risk"] >= 30)
                & (intelligence["risk"] < 50)
            ).sum()
        ),
        "stable": int(
            (intelligence["risk"] < 30).sum()
        ),
        "avg_utilization": round(
            float(intelligence["utilization"].mean()),
            1,
        ),
        "beds_available": int(
            (
                df["beds"]
                * (1 - df["utilization"])
            )
            .groupby(df["phc_id"])
            .first()
            .sum()
        ),
        "last_updated": "Live simulation",
    }


@app.get("/api/phcs")
def phcs():

    return build_phc_intelligence(df)


@app.get("/api/intelligence")
def intelligence():

    records = build_phc_intelligence(df)

    return {
        "total_phcs": len(records),
        "critical": [
            item
            for item in records
            if item["risk"] >= 75
        ],
        "high_risk": [
            item
            for item in records
            if 50 <= item["risk"] < 75
        ],
        "watch": [
            item
            for item in records
            if 30 <= item["risk"] < 50
        ],
    }


@app.get("/api/medicines")
def medicines():

    output = []

    for medicine, group in df.groupby("medicine"):

        stock = float(group["stock"].sum())
        daily_demand = float(
            group["daily_demand"].sum()
        )

        analysis = {
            "stock": stock,
            "daily_demand": daily_demand,
        }

        days_cover = (
            stock / max(daily_demand, 1)
        )

        if days_cover <= 2:
            risk = 95
        elif days_cover <= 4:
            risk = 82
        elif days_cover <= 7:
            risk = 65
        elif days_cover <= 10:
            risk = 40
        else:
            risk = 15

        forecast = forecast_demand(
            daily_demand,
            days=7,
        )

        output.append(
            {
                "medicine": medicine,
                "stock": int(stock),
                "daily_demand": round(
                    daily_demand,
                    1,
                ),
                "days_cover": round(
                    days_cover,
                    1,
                ),
                "forecast_7d": round(
                    forecast["total_forecast"],
                    0,
                ),
                "risk": risk,
                "status": risk_level(risk),
            }
        )

    return output


@app.get("/api/stockouts")
def stockouts():

    risks = find_stockout_risks(df)

    return {
        "count": len(risks),
        "items": risks[:30],
    }


@app.get("/api/forecast/{phc_id}")
def forecast(
    phc_id: str,
    medicine: Optional[str] = "Paracetamol",
):

    group = df[
        (df["phc_id"] == phc_id)
        & (df["medicine"] == medicine)
    ]

    if group.empty:
        return {
            "error": "PHC or medicine not found"
        }

    base_demand = float(
        group["daily_demand"].iloc[0]
    )

    result = forecast_demand(
        base_daily_demand=base_demand,
        days=7,
    )

    return {
        "phc_id": phc_id,
        "medicine": medicine,
        "history": result["history"],
        "forecast": result["forecast"],
        "total_forecast": result["total_forecast"],
        "model": "Linear demand forecasting model",
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

    critical = sorted(
        intelligence,
        key=lambda item: item["risk"],
        reverse=True,
    )

    critical = [
        item
        for item in critical
        if item["risk"] >= 75
    ][:10]

    stockouts = find_stockout_risks(
        df,
        demand_multiplier=multiplier,
    )

    return {
        "outbreak": req.outbreak,
        "demand_multiplier": multiplier,
        "critical_count": len(
            [
                item
                for item in intelligence
                if item["risk"] >= 75
            ]
        ),
        "critical_phcs": critical,
        "stockout_risks": stockouts[:15],
        "message": (
            "Emergency demand simulation completed. "
            "Prioritize critical PHCs and redistribute "
            "resources from lower-risk facilities."
        ),
    }


@app.get("/api/recommendations")
def recommendations():
    """
    Generate AI-assisted medicine redistribution recommendations.

    The recommendation engine evaluates medicine-level stock,
    projected seven-day demand, days of cover, stock-out risk,
    and PHC operational risk before proposing transfers.
    """

    return generate_redistribution_recommendations(
        df=df,
        demand_multiplier=1.0,
    )

    intelligence = pd.DataFrame(
        build_phc_intelligence(df)
    )

    donors = intelligence[
        intelligence["risk"] < 30
    ].sort_values(
        "avg_stock_days",
        ascending=False,
    )

    receivers = intelligence[
        intelligence["risk"] >= 60
    ].sort_values(
        "risk",
        ascending=False,
    )

    recommendations = []

    for index, (_, receiver) in enumerate(
        receivers.head(8).iterrows()
    ):

        if donors.empty:
            break

        donor = donors.iloc[
            index % len(donors)
        ]

        medicine = MEDICINES[
            index % len(MEDICINES)
        ]

        quantity = int(
            250
            + (
                receiver["risk"] - 60
            ) * 12
        )

        recommendations.append(
            {
                "from_phc": donor["phc_id"],
                "from_district": donor["district"],
                "to_phc": receiver["phc_id"],
                "to_district": receiver["district"],
                "medicine": medicine,
                "quantity": quantity,
                "priority": (
                    "Urgent"
                    if receiver["risk"] >= 75
                    else "High"
                ),
                "reason": (
                    f'{receiver["phc_id"]} has '
                    f'{receiver["avg_stock_days"]} days '
                    f'of stock cover and '
                    f'{receiver["risk"]}% operational risk.'
                ),
            }
        )

    return recommendations