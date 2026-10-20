"""core/graph/scoring.py - Lightweight, deterministic heuristic ML scoring functions.

Computes:
1. Machine failure risk & predicted failure days from synthetic sensor drift
   (z-score of recent vibration and temperature readings vs historical baseline).
2. Product 30-day demand forecast from historical sales using Exponential Smoothing.
"""

from typing import List, Dict, Tuple
import math


def compute_machine_risk(
    recent_readings: List[Dict[str, float]],
    baseline_stats: Dict[str, Dict[str, float]],
) -> Tuple[float, int]:
    """Calculate machine failure risk (0.0 - 1.0) and predicted failure days.
    
    Uses z-score of recent sensor readings (temperature and vibration)
    relative to calibrated baselines:
      z = (mean(recent) - baseline_mean) / baseline_std
    Composite z-score is mapped via a sigmoid transfer function.
    """
    if not recent_readings:
        return 0.1, 90

    # Extract recent temperatures and vibrations
    temps = [r.get("temperature", 65.0) for r in recent_readings]
    vibes = [r.get("vibration", 1.2) for r in recent_readings]

    avg_temp = sum(temps) / len(temps)
    avg_vibe = sum(vibes) / len(vibes)

    t_mean = baseline_stats.get("temperature", {}).get("mean", 65.0)
    t_std = max(baseline_stats.get("temperature", {}).get("std", 2.5), 0.1)

    v_mean = baseline_stats.get("vibration", {}).get("mean", 1.2)
    v_std = max(baseline_stats.get("vibration", {}).get("std", 0.15), 0.01)

    z_temp = max(0.0, (avg_temp - t_mean) / t_std)
    z_vibe = max(0.0, (avg_vibe - v_mean) / v_std)

    # Weighted composite z-score (vibration is weighted higher for mechanical breakdown)
    composite_z = 0.6 * z_vibe + 0.4 * z_temp

    # Sigmoid mapping centered at z=2.0 (standard 2-sigma drift alert)
    # failure_risk: 0.0 to 1.0
    failure_risk = 1.0 / (1.0 + math.exp(-1.5 * (composite_z - 2.0)))
    failure_risk = round(max(0.01, min(0.99, failure_risk)), 2)

    # Predicted days until critical failure based on risk
    if failure_risk >= 0.85:
        # Imminent failure: 3 - 6 days
        predicted_days = max(2, int(15 * (1.0 - failure_risk)))
    elif failure_risk >= 0.50:
        predicted_days = int(25 * (1.0 - failure_risk)) + 7
    else:
        # Healthy machine
        predicted_days = int(80 + (1.0 - failure_risk) * 50)

    return failure_risk, predicted_days


def compute_demand_forecast(
    sales_history: List[int],
    alpha: float = 0.35,
) -> int:
    """Compute 30-day forward demand forecast using Single Exponential Smoothing.
    
    Formula: S_t = alpha * Y_t + (1 - alpha) * S_{t-1}
    Projects next period and scales to 30-day horizon.
    """
    if not sales_history:
        return 500

    s = float(sales_history[0])
    for y in sales_history[1:]:
        s = alpha * float(y) + (1.0 - alpha) * s

    # Round to nearest integer units
    forecast_30d = int(round(s))
    return max(10, forecast_30d)


def compute_safety_stock(forecast_30d: int, lead_time_days: int = 10, service_factor: float = 1.65) -> int:
    """Standard buffer safety stock calculation based on demand variability."""
    # Approximate demand standard deviation as 15% of monthly forecast
    demand_std_daily = (forecast_30d * 0.15) / math.sqrt(30)
    safety_stock = int(service_factor * demand_std_daily * math.sqrt(lead_time_days))
    return max(20, safety_stock)
