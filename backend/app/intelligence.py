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
    Calculate an operational PHC risk score using:
    - medicine stock pressure
    - facility utilization
    - staff pressure
    - emergency demand pressure
    """

    stock_pressure = max(0.0, 7.0 - stock_days) * 10.5

    utilization_pressure = max(
        0.0,
        utilization - 0.55,
    ) * 55

    staff_ratio = staff / max(beds, 1)

    staff_pressure = max(
        0.0,
        0.25 - staff_ratio,
    ) * 80

    emergency_pressure = max(
        0.0,
        demand_multiplier - 1.0,
    ) * 48

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
    """

    base = max(float(base_daily_demand), 1.0)

    history = []

    for day in range(14):
        trend = 0.82 + (day * 0.025)
        seasonal = 1 + np.sin(day / 2.5) * 0.035

        value = base * trend * seasonal

        history.append(
            round(max(10.0, value), 1)
        )

    x = np.arange(
        len(history)
    ).reshape(-1, 1)

    y = np.array(history)

    model = LinearRegression()

    model.fit(x, y)

    future_x = np.arange(
        len(history),
        len(history) + days,
    ).reshape(-1, 1)

    predictions = model.predict(future_x)

    predictions = np.maximum(
        predictions,
        0,
    )

    return {
        "history": history,
        "forecast": [
            round(float(v), 1)
            for v in predictions
        ],
        "total_forecast": round(
            float(predictions.sum()),
            1,
        ),
    }


def stockout_analysis(
    stock: float,
    daily_demand: float,
    demand_multiplier: float = 1.0,
) -> Dict:
    """Estimate medicine days of cover and stock-out risk."""

    adjusted_daily_demand = max(
        float(daily_demand) * demand_multiplier,
        1.0,
    )

    days_cover = (
        float(stock)
        / adjusted_daily_demand
    )

    seven_day_demand = (
        adjusted_daily_demand * 7
    )

    shortage = max(
        0.0,
        seven_day_demand - float(stock),
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

    if demand_multiplier > 1:
        risk += (
            demand_multiplier - 1
        ) * 25

    risk = round(
        float(np.clip(risk, 0, 99)),
        1,
    )

    return {
        "days_cover": round(
            float(days_cover),
            1,
        ),
        "seven_day_demand": round(
            float(seven_day_demand),
            1,
        ),
        "shortage": round(
            float(shortage),
            1,
        ),
        "risk": risk,
        "status": risk_level(risk),
    }


def generate_reason(
    risk: float,
    stock_days: float,
    utilization: float,
) -> str:
    """Generate an explainable operational reason."""

    reasons = []

    if stock_days < 4:
        reasons.append(
            f"only {stock_days:.1f} days of stock cover"
        )

    if utilization > 80:
        reasons.append(
            f"{utilization:.0f}% facility utilization"
        )

    if not reasons:
        reasons.append(
            "stable stock and utilization indicators"
        )

    if risk >= 75:
        return (
            "Critical: "
            + " and ".join(reasons)
            + "."
        )

    if risk >= 50:
        return (
            "High risk: "
            + " and ".join(reasons)
            + "."
        )

    if risk >= 30:
        return (
            "Watch: "
            + " and ".join(reasons)
            + "."
        )

    return (
        "Stable: "
        + " and ".join(reasons)
        + "."
    )


def build_phc_intelligence(
    df: pd.DataFrame,
    demand_multiplier: float = 1.0,
) -> List[Dict]:

    results = []

    for phc_id, group in df.groupby("phc_id"):

        utilization = float(
            group["utilization"].iloc[0]
        )

        beds = int(
            group["beds"].iloc[0]
        )

        staff = int(
            group["staff"].iloc[0]
        )

        weighted_stock_days = (
            (
                group["stock_days"]
                * group["daily_demand"]
            ).sum()
            / max(
                group["daily_demand"].sum(),
                1,
            )
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
                "latitude": float(
                    group["latitude"].iloc[0]
                ),
                "longitude": float(
                    group["longitude"].iloc[0]
                ),
                "beds": beds,
                "staff": staff,
                "utilization": round(
                    utilization * 100,
                    1,
                ),
                "avg_stock_days": round(
                    float(weighted_stock_days),
                    1,
                ),
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
            daily_demand=float(
                row["daily_demand"]
            ),
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
                    "daily_demand": round(
                        float(row["daily_demand"]),
                        1,
                    ),
                    **analysis,
                }
            )

    return sorted(
        results,
        key=lambda item: item["risk"],
        reverse=True,
    )


# ============================================================
# AI RESOURCE REDISTRIBUTION ENGINE
# ============================================================

def generate_redistribution_recommendations(
    df: pd.DataFrame,
    demand_multiplier: float = 1.0,
) -> List[Dict]:
    """
    Identify PHCs that may need medicine transfers from
    PHCs holding sufficient reserve stock.

    The engine considers:
    - projected 7-day demand
    - current stock
    - days of cover
    - shortage quantity
    - PHC operational risk
    - available donor surplus

    This is a decision-support recommendation, not an
    autonomous medical decision.
    """

    working = df.copy()

    # Calculate medicine-level stock intelligence
    analyses = []

    for _, row in working.iterrows():

        analysis = stockout_analysis(
            stock=float(row["stock"]),
            daily_demand=float(
                row["daily_demand"]
            ),
            demand_multiplier=demand_multiplier,
        )

        analyses.append(
            {
                "phc_id": row["phc_id"],
                "district": row["district"],
                "state": row["state"],
                "medicine": row["medicine"],
                "stock": float(row["stock"]),
                "daily_demand": float(
                    row["daily_demand"]
                ),
                "days_cover": analysis[
                    "days_cover"
                ],
                "seven_day_demand": analysis[
                    "seven_day_demand"
                ],
                "shortage": analysis[
                    "shortage"
                ],
                "risk": analysis["risk"],
                "status": analysis["status"],
            }
        )

    if not analyses:
        return []

    # --------------------------------------------------------
    # Build PHC-level risk scores
    # --------------------------------------------------------

    phc_intelligence = build_phc_intelligence(
        working,
        demand_multiplier,
    )

    phc_risk_map = {
        item["phc_id"]: item
        for item in phc_intelligence
    }

    # --------------------------------------------------------
    # Group medicine records
    # --------------------------------------------------------

    recommendations = []

    medicines = sorted(
        {
            item["medicine"]
            for item in analyses
        }
    )

    for medicine in medicines:

        medicine_rows = [
            item
            for item in analyses
            if item["medicine"] == medicine
        ]

        receivers = []
        donors = []

        for item in medicine_rows:

            phc_info = phc_risk_map.get(
                item["phc_id"],
                {},
            )

            phc_risk = float(
                phc_info.get("risk", 0)
            )

            # A receiver is a PHC where:
            # - stock cover is <= 7 days OR
            # - stockout risk is >= 50 OR
            # - operational PHC risk is high
            if (
                item["days_cover"] <= 7
                or item["risk"] >= 50
                or phc_risk >= 50
            ):

                required = max(
                    0.0,
                    item["seven_day_demand"]
                    - item["stock"],
                )

                # Even if the calculated shortage is small,
                # a high-risk PHC should still be considered.
                if required <= 0 and (
                    item["days_cover"] <= 4
                    or item["risk"] >= 65
                ):
                    required = max(
                        1.0,
                        item["daily_demand"] * 2,
                    )

                if required > 0:

                    receivers.append(
                        {
                            **item,
                            "phc_risk": phc_risk,
                            "required": required,
                        }
                    )

            # A donor should have more than 10 days
            # of medicine cover.
            donor_surplus = (
                item["stock"]
                - (
                    item["daily_demand"]
                    * demand_multiplier
                    * 10
                )
            )

            if (
                item["days_cover"] > 10
                and donor_surplus > 0
            ):

                donors.append(
                    {
                        **item,
                        "phc_risk": phc_risk,
                        "surplus": donor_surplus,
                    }
                )

        # ----------------------------------------------------
        # Match receivers with donors
        # ----------------------------------------------------

        receivers.sort(
            key=lambda x: (
                -x["risk"],
                x["days_cover"],
            )
        )

        donors.sort(
            key=lambda x: x["surplus"],
            reverse=True,
        )

        for receiver in receivers:

            possible_donors = [
                donor
                for donor in donors
                if donor["phc_id"]
                != receiver["phc_id"]
            ]

            if not possible_donors:
                continue

            donor = possible_donors[0]

            transfer_quantity = min(
                receiver["required"],
                donor["surplus"],
            )

            transfer_quantity = int(
                max(
                    1,
                    round(transfer_quantity),
                )
            )

            if transfer_quantity <= 0:
                continue

            # Explainable recommendation reason
            if receiver["days_cover"] <= 2:
                urgency = "critical stock-out risk"

            elif receiver["days_cover"] <= 4:
                urgency = "low medicine cover"

            else:
                urgency = "elevated demand pressure"

            reason = (
                f"{receiver['phc_id']} has "
                f"{receiver['days_cover']:.1f} days of "
                f"{medicine} cover and shows "
                f"{urgency}. "
                f"{donor['phc_id']} has "
                f"{donor['days_cover']:.1f} days of reserve."
            )

            recommendations.append(
                {
                    "from_phc": donor["phc_id"],
                    "from_district": donor["district"],
                    "from_state": donor["state"],
                    "to_phc": receiver["phc_id"],
                    "to_district": receiver["district"],
                    "to_state": receiver["state"],
                    "medicine": medicine,
                    "quantity": transfer_quantity,
                    "receiver_risk": receiver["risk"],
                    "receiver_status": receiver[
                        "status"
                    ],
                    "receiver_days_cover": round(
                        receiver["days_cover"],
                        1,
                    ),
                    "donor_days_cover": round(
                        donor["days_cover"],
                        1,
                    ),
                    "reason": reason,
                    "priority": (
                        "Critical"
                        if receiver["risk"] >= 75
                        else "High"
                        if receiver["risk"] >= 50
                        else "Watch"
                    ),
                    "action": (
                        f"Transfer {transfer_quantity} "
                        f"units of {medicine} from "
                        f"{donor['phc_id']} to "
                        f"{receiver['phc_id']}."
                    ),
                }
            )

            # Reduce donor surplus so we don't recommend
            # distributing the same stock multiple times.
            donor["surplus"] -= transfer_quantity

            if donor["surplus"] <= 0:
                donors.remove(donor)

    # Highest urgency first
    priority_order = {
        "Critical": 0,
        "High": 1,
        "Watch": 2,
    }

    recommendations.sort(
        key=lambda x: (
            priority_order.get(
                x["priority"],
                3,
            ),
            -x["receiver_risk"],
        )
    )

    return recommendations