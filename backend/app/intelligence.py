from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


RISK_THRESHOLDS = {
    "critical": 75,
    "high": 50,
    "watch": 30,
}


def risk_level(risk: float) -> str:
    """Convert a numerical risk score into an operational category."""
    if risk >= RISK_THRESHOLDS["critical"]:
        return "Critical"
    if risk >= RISK_THRESHOLDS["high"]:
        return "High"
    if risk >= RISK_THRESHOLDS["watch"]:
        return "Watch"
    return "Stable"


def calculate_phc_risk(
    utilization: float,
    stock_days: float,
    staff: int,
    beds: int,
    demand_multiplier: float = 1.0,
) -> float:
    """
    Calculate a lightweight operational risk score.

    The score combines:
    - low medicine stock cover
    - high facility utilization
    - staff pressure
    - emergency demand multiplier
    """

    stock_pressure = max(0.0, 7.0 - stock_days) * 10.5
    utilization_pressure = max(0.0, utilization - 0.55) * 55

    staff_ratio = staff / max(beds, 1)
    staff_pressure = max(0.0, 0.25 - staff_ratio) * 80

    emergency_pressure = max(0.0, demand_multiplier - 1.0) * 48

    score = (
        stock_pressure
        + utilization_pressure
        + staff_pressure
        + emergency_pressure
    )

    return round(float(np.clip(score, 0, 99)), 1)


def forecast_demand(
    base_daily_demand: float,
    days: int = 7,
) -> Dict[str, List[float]]:
    """
    Forecast medicine demand using a lightweight linear trend model.

    This is intentionally simple for the hackathon MVP and can later
    be replaced with a time-series model.
    """

    base = max(float(base_daily_demand), 1.0)

    history = []

    for day in range(14):
        trend = 0.82 + (day * 0.025)
        seasonal = 1 + np.sin(day / 2.5) * 0.035
        value = base * trend * seasonal
        history.append(round(max(10.0, value), 1))

    x = np.arange(len(history)).reshape(-1, 1)
    y = np.array(history)

    model = LinearRegression()
    model.fit(x, y)

    future_x = np.arange(len(history), len(history) + days).reshape(-1, 1)
    predictions = model.predict(future_x)

    predictions = np.maximum(predictions, 0)

    return {
        "history": history,
        "forecast": [round(float(v), 1) for v in predictions],
        "total_forecast": round(float(predictions.sum()), 1),
    }


def stockout_analysis(
    stock: float,
    daily_demand: float,
    demand_multiplier: float = 1.0,
) -> Dict:
    """Estimate days of cover and stock-out risk."""

    adjusted_daily_demand = max(
        float(daily_demand) * demand_multiplier,
        1.0,
    )

    days_cover = stock / adjusted_daily_demand

    seven_day_demand = adjusted_daily_demand * 7
    shortage = max(0.0, seven_day_demand - stock)

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

    if demand_multiplier > 1:
        risk += (demand_multiplier - 1) * 25

    risk = round(float(np.clip(risk, 0, 99)), 1)

    return {
        "days_cover": round(float(days_cover), 1),
        "seven_day_demand": round(float(seven_day_demand), 1),
        "shortage": round(float(shortage), 1),
        "risk": risk,
        "status": risk_level(risk),
    }


def generate_reason(
    risk: float,
    stock_days: float,
    utilization: float,
) -> str:
    """Generate an explainable operational reason for the risk score."""

    reasons = []

    if stock_days < 4:
        reasons.append(f"only {stock_days:.1f} days of stock cover")

    if utilization > 80:
        reasons.append(f"{utilization:.0f}% facility utilization")

    if not reasons:
        reasons.append("stable stock and utilization indicators")

    if risk >= 75:
        return "Critical: " + " and ".join(reasons) + "."

    if risk >= 50:
        return "High risk: " + " and ".join(reasons) + "."

    if risk >= 30:
        return "Watch: " + " and ".join(reasons) + "."

    return "Stable: " + " and ".join(reasons) + "."


def build_phc_intelligence(
    df: pd.DataFrame,
    demand_multiplier: float = 1.0,
) -> List[Dict]:

    results = []

    for phc_id, group in df.groupby("phc_id"):

        utilization = float(group["utilization"].iloc[0])
        beds = int(group["beds"].iloc[0])
        staff = int(group["staff"].iloc[0])

        weighted_stock_days = (
            (group["stock_days"] * group["daily_demand"]).sum()
            / max(group["daily_demand"].sum(), 1)
        )

        risk = calculate_phc_risk(
            utilization=utilization,
            stock_days=weighted_stock_days,
            staff=staff,
            beds=beds,
            demand_multiplier=demand_multiplier,
        )

        results.append(
            {
                "phc_id": phc_id,
                "district": group["district"].iloc[0],
                "state": group["state"].iloc[0],
                "latitude": float(group["latitude"].iloc[0]),
                "longitude": float(group["longitude"].iloc[0]),
                "beds": beds,
                "staff": staff,
                "utilization": round(utilization * 100, 1),
                "avg_stock_days": round(float(weighted_stock_days), 1),
                "risk": risk,
                "status": risk_level(risk),
                "reason": generate_reason(
                    risk,
                    weighted_stock_days,
                    utilization * 100,
                ),
            }
        )

    return results


def find_stockout_risks(
    df: pd.DataFrame,
    demand_multiplier: float = 1.0,
) -> List[Dict]:

    results = []

    for _, row in df.iterrows():

        analysis = stockout_analysis(
            stock=float(row["stock"]),
            daily_demand=float(row["daily_demand"]),
            demand_multiplier=demand_multiplier,
        )

        if analysis["risk"] >= 50:
            results.append(
                {
                    "phc_id": row["phc_id"],
                    "district": row["district"],
                    "state": row["state"],
                    "medicine": row["medicine"],
                    "stock": int(row["stock"]),
                    "daily_demand": round(float(row["daily_demand"]), 1),
                    **analysis,
                }
            )

    return sorted(
        results,
        key=lambda item: item["risk"],
        reverse=True,
    )