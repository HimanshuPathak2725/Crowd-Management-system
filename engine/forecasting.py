"""
forecasting.py
---------------
Per-zone occupancy/density forecasting, updated online every simulation tick.

Design choice: instead of one global model, each zone gets its own small
online regressor. Venue zones have very different dynamics (a grandstand
fills and drains completely differently from a food court), so a
per-zone model with lag features converges faster and is cheap enough to
retrain every tick (O(zones), not O(zones^2) like a full graph-neural model
would need, which is overkill for a hackathon-scale demo and still not
justified at real venue scale without months of historical data to train on).

Model: scikit-learn SGDRegressor (linear model, incrementally trained via
partial_fit) on lag features [density(t), velocity(t), accel(t), rolling
mean(t)] -> density(t + horizon). Falls back to a Holt's linear trend
extrapolation until a zone has collected enough history to train on
(cold-start problem every real forecasting system has to handle).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np
from sklearn.linear_model import SGDRegressor


@dataclass
class ZoneForecast:
    zone_id: str
    horizon_ticks: int
    predicted_density: float
    predicted_occupancy: int
    current_density: float
    trend_ppl_per_tick: float
    confidence: str  # "low" (cold start / trend fallback) or "model" (trained regressor)


class ZoneModel:
    def __init__(self, horizon_ticks: int, min_history: int = 12):
        self.horizon_ticks = horizon_ticks
        self.min_history = min_history
        self.history: deque[float] = deque(maxlen=200)
        self.reg = SGDRegressor(max_iter=1, tol=None, learning_rate="invscaling",
                                 eta0=0.01, warm_start=True)
        self._fitted = False

    @staticmethod
    def _features(hist: list[float], t: int) -> np.ndarray:
        d0 = hist[t]
        d1 = hist[t - 1] if t >= 1 else d0
        d2 = hist[t - 2] if t >= 2 else d1
        velocity = d0 - d1
        accel = (d0 - d1) - (d1 - d2)
        window = hist[max(0, t - 5):t + 1]
        rolling_mean = sum(window) / len(window)
        return np.array([[d0, velocity, accel, rolling_mean]])

    def update(self, density: float) -> None:
        self.history.append(density)
        hist = list(self.history)
        t = len(hist) - 1
        target_idx = t - self.horizon_ticks
        if target_idx >= 2:  # need t-2 to build lag features for the target point
            X = self._features(hist, target_idx)
            y = np.array([hist[t]])
            self.reg.partial_fit(X, y)
            self._fitted = True

    def predict(self) -> tuple[float, float, str]:
        hist = list(self.history)
        if not hist:
            return 0.0, 0.0, "low"
        t = len(hist) - 1
        trend = hist[t] - hist[t - 1] if t >= 1 else 0.0
        if self._fitted and len(hist) >= self.min_history:
            X = self._features(hist, t)
            pred = float(self.reg.predict(X)[0])
            return max(0.0, pred), trend, "model"
        # cold-start fallback: simple linear extrapolation of current trend
        pred = max(0.0, hist[t] + trend * self.horizon_ticks)
        return pred, trend, "low"


class ForecastingEngine:
    def __init__(self, zone_ids: list[str], horizon_ticks: int = 6):
        self.horizon_ticks = horizon_ticks
        self.models: dict[str, ZoneModel] = {
            zid: ZoneModel(horizon_ticks=horizon_ticks) for zid in zone_ids
        }

    def update(self, densities: dict[str, float]) -> None:
        for zid, d in densities.items():
            self.models[zid].update(d)

    def forecast(self, zone_areas: dict[str, float]) -> dict[str, ZoneForecast]:
        out = {}
        for zid, model in self.models.items():
            pred_density, trend, confidence = model.predict()
            out[zid] = ZoneForecast(
                zone_id=zid,
                horizon_ticks=self.horizon_ticks,
                predicted_density=round(pred_density, 3),
                predicted_occupancy=int(round(pred_density * zone_areas[zid])),
                current_density=round(model.history[-1], 3) if model.history else 0.0,
                trend_ppl_per_tick=round(trend, 4),
                confidence=confidence,
            )
        return out
