"""
bottleneck.py
--------------
Turns the raw per-zone forecasts into ranked alerts a control-room operator
(or the auto-rerouting engine) can act on, using the Fruin Level-of-Service
thresholds already attached to the venue definition.

An alert fires when the *forecasted* density crosses "at_risk", not the
*current* density - the entire point of forecasting is to get lead time
(horizon_ticks * dt_s seconds) before the zone is actually dangerous.
"""
from __future__ import annotations

from dataclasses import dataclass

from .forecasting import ZoneForecast
from .venue import Venue


@dataclass
class BottleneckAlert:
    zone_id: str
    zone_name: str
    current_density: float
    predicted_density: float
    los_now: str
    los_predicted: str
    lead_time_s: int
    severity: float  # predicted_density / at_risk_threshold, for ranking
    trend_ppl_per_tick: float


class BottleneckDetector:
    def __init__(self, venue: Venue, dt_s: int):
        self.venue = venue
        self.dt_s = dt_s

    def detect(self, forecasts: dict[str, ZoneForecast]) -> list[BottleneckAlert]:
        at_risk = self.venue.los_thresholds["at_risk"]
        alerts: list[BottleneckAlert] = []
        for zid, f in forecasts.items():
            if f.predicted_density < at_risk:
                continue
            zone = self.venue.zones[zid]
            alerts.append(BottleneckAlert(
                zone_id=zid,
                zone_name=zone.name,
                current_density=f.current_density,
                predicted_density=f.predicted_density,
                los_now=self.venue.los_level(f.current_density),
                los_predicted=self.venue.los_level(f.predicted_density),
                lead_time_s=f.horizon_ticks * self.dt_s,
                severity=round(f.predicted_density / at_risk, 2),
                trend_ppl_per_tick=f.trend_ppl_per_tick,
            ))
        alerts.sort(key=lambda a: a.severity, reverse=True)
        return alerts
