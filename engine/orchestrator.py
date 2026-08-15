"""
orchestrator.py
-----------------
Wires the four subsystems together into a single ticking digital twin and
exposes one JSON-serialisable `state()` snapshot the API / dashboard reads
each tick. This is the class both `scripts/run_demo.py` (headless CLI) and
`server/app.py` (live web dashboard) call.
"""
from __future__ import annotations

import time
from dataclasses import asdict

from .bottleneck import BottleneckDetector
from .forecasting import ForecastingEngine
from .rerouting import ReroutingEngine
from .simulation import CrowdSimulation
from .venue import Venue


class DigitalTwin:
    def __init__(self, venue_path: str, dt_s: int = 10, horizon_ticks: int = 6):
        self.venue = Venue.from_json(venue_path)
        self.sim = CrowdSimulation(self.venue, dt_s=dt_s)
        self.forecaster = ForecastingEngine(list(self.venue.zones.keys()), horizon_ticks=horizon_ticks)
        self.detector = BottleneckDetector(self.venue, dt_s=dt_s)
        self.rerouter = ReroutingEngine(self.venue, self.sim)
        self.tick_count = 0
        self.alert_log: list[dict] = []
        self.reroute_log: list[dict] = []

    def ingest_vision_observation(self, zone_id: str, occupancy: int) -> None:
        """Inject a calibrated CCTV observation before the next simulation tick."""
        if zone_id not in self.venue.zones:
            return
        zone = self.venue.zones[zone_id]
        zone.occupancy = max(0, min(int(occupancy), zone.capacity))

    def tick(self) -> dict:
        self.sim.step()
        densities = {zid: z.density for zid, z in self.venue.zones.items()}
        self.forecaster.update(densities)
        areas = {zid: z.area_sqm for zid, z in self.venue.zones.items()}
        forecasts = self.forecaster.forecast(areas)
        alerts = self.detector.detect(forecasts)
        suggestions = self.rerouter.apply(alerts)
        self.tick_count += 1

        if alerts:
            self.alert_log.append({"tick": self.tick_count, "sim_time_s": self.sim.sim_time_s,
                                    "alerts": [asdict(a) for a in alerts]})
            self.alert_log = self.alert_log[-50:]
        if suggestions:
            self.reroute_log.append({"tick": self.tick_count, "sim_time_s": self.sim.sim_time_s,
                                      "suggestions": [asdict(s) for s in suggestions]})
            self.reroute_log = self.reroute_log[-50:]

        return self.state(forecasts, alerts, suggestions)

    def state(self, forecasts=None, alerts=None, suggestions=None) -> dict:
        snap = self.sim.snapshot()
        return {
            "tick": self.tick_count,
            "sim_time_s": snap["sim_time_s"],
            "phase": snap["phase"],
            "total_occupancy": snap["total_occupancy"],
            "zones": [
                {
                    "id": zid,
                    "name": z.name,
                    "type": z.type,
                    "x": z.x, "y": z.y,
                    "capacity": z.capacity,
                    "occupancy": snap["zones"][zid]["occupancy"],
                    "density": snap["zones"][zid]["density"],
                    "los": snap["zones"][zid]["los"],
                    "forecast": (asdict(forecasts[zid]) if forecasts else None),
                }
                for zid, z in self.venue.zones.items()
            ],
            "edges": [
                {"from": u, "to": v, "flow_ppl_per_min": round(d["flow"], 1),
                 "capacity_ppl_per_min": d["capacity_ppl_per_min"],
                 "steer_bias": round(self.sim.steer_bias.get((u, v), 1.0), 2)}
                for u, v, d in self.venue.graph.edges(data=True)
            ],
            "alerts": [a.__dict__ for a in (alerts or [])],
            "reroutes": [s.__dict__ for s in (suggestions or [])],
            "alert_log": self.alert_log[-10:],
            "reroute_log": self.reroute_log[-10:],
        }

    def run_headless(self, ticks: int, wall_delay_s: float = 0.0):
        for _ in range(ticks):
            snap = self.tick()
            if wall_delay_s:
                time.sleep(wall_delay_s)
            yield snap
