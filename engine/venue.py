"""
venue.py
--------
Loads the venue topology (zones + walkways) into a NetworkX graph that the
rest of the engine (simulation, forecasting, rerouting) operates on.

A "zone" is any bounded area with a floor area (sqm) and a max capacity.
An "edge" is a walkway/corridor connecting two zones with a physical width
and a derived flow capacity (people/min), following the standard pedestrian
engineering assumption that pathway throughput scales with width
(Fruin, "Pedestrian Planning and Design").
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx


@dataclass
class Zone:
    id: str
    name: str
    x: float
    y: float
    area_sqm: float
    capacity: int
    type: str
    occupancy: int = 0

    @property
    def density(self) -> float:
        """People per square metre - the standard crowd-safety unit (Fruin LOS)."""
        return self.occupancy / self.area_sqm if self.area_sqm else 0.0


@dataclass
class Venue:
    graph: nx.DiGraph
    zones: dict[str, Zone] = field(default_factory=dict)
    los_thresholds: dict[str, float] = field(default_factory=dict)
    entry_zones: list[str] = field(default_factory=list)
    exit_zones: list[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: str | Path) -> "Venue":
        data = json.loads(Path(path).read_text())
        g = nx.DiGraph()
        zones: dict[str, Zone] = {}

        for z in data["zones"]:
            zone = Zone(
                id=z["id"], name=z["name"], x=z["x"], y=z["y"],
                area_sqm=z["area_sqm"], capacity=z["capacity"], type=z["type"],
            )
            zones[zone.id] = zone
            g.add_node(zone.id, **z)

        for e in data["edges"]:
            # walkways are treated as bidirectional; base weight = length_m,
            # the rerouting engine later augments this with a congestion penalty.
            for a, b in ((e["from"], e["to"]), (e["to"], e["from"])):
                g.add_edge(
                    a, b,
                    base_weight=e["length_m"],
                    capacity_ppl_per_min=e["capacity_ppl_per_min"],
                    width_m=e["width_m"],
                    flow=0.0,               # current people/min flowing this way, updated by sim
                )

        entry_zones = [z.id for z in zones.values() if z.type == "entry"]
        exit_zones = [z.id for z in zones.values() if z.type == "exit"]

        return cls(
            graph=g, zones=zones,
            los_thresholds=data["meta"]["density_los_thresholds_ppl_per_sqm"],
            entry_zones=entry_zones, exit_zones=exit_zones,
        )

    def neighbors(self, zone_id: str) -> list[str]:
        return list(self.graph.successors(zone_id))

    def total_occupancy(self) -> int:
        return sum(z.occupancy for z in self.zones.values())

    def los_level(self, density: float) -> str:
        t = self.los_thresholds
        if density >= t["crush_risk"]:
            return "crush_risk"
        if density >= t["at_risk"]:
            return "at_risk"
        if density >= t["congested"]:
            return "congested"
        if density >= t["comfortable"]:
            return "busy"
        return "comfortable"
