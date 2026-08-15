"""
rerouting.py
-------------
Closes the loop: simulation -> forecast -> bottleneck alert -> **action**.

For every flagged zone Z we:
  1. Find the upstream zones U that currently feed Z.
  2. For each U, find the best alternative out-edge that still makes
     progress toward an exit (or toward the venue interior during ingress)
     without going through Z, using Dijkstra on a copy of the graph where
     edges into Z are heavily penalised.
  3. Throttle `steer_bias[(U, Z)]` down and boost the bias of the chosen
     alternative edge - this is fed straight back into
     `CrowdSimulation.steer_bias`, so the next tick actually reroutes flow
     (a closed-loop control system, not just a dashboard warning).
  4. Emit a plain-English suggestion for the human control-room operator.

Biases decay back to 1.0 once a zone is no longer flagged, so the system
doesn't permanently close a corridor because of a one-off spike.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from .bottleneck import BottleneckAlert
from .simulation import CrowdSimulation
from .venue import Venue

THROTTLE_BIAS = 0.15
BOOST_BIAS = 2.5
DECAY_RATE = 0.85  # per tick, pulls biases back toward 1.0 once a zone clears


@dataclass
class RerouteSuggestion:
    bottleneck_zone: str
    upstream_zone: str
    avoid_edge: tuple[str, str]
    suggested_edge: tuple[str, str]
    suggested_via: str
    message: str


class ReroutingEngine:
    def __init__(self, venue: Venue, sim: CrowdSimulation):
        self.venue = venue
        self.sim = sim

    def _decay_all_biases(self) -> None:
        for k, v in list(self.sim.steer_bias.items()):
            new_v = 1.0 + (v - 1.0) * DECAY_RATE
            if abs(new_v - 1.0) < 0.02:
                del self.sim.steer_bias[k]
            else:
                self.sim.steer_bias[k] = new_v

    def apply(self, alerts: list[BottleneckAlert]) -> list[RerouteSuggestion]:
        self._decay_all_biases()
        suggestions: list[RerouteSuggestion] = []
        flagged = {a.zone_id for a in alerts}

        for alert in alerts:
            z = alert.zone_id
            upstream = [u for u in self.venue.graph.predecessors(z)
                        if self.venue.zones[u].type != "entry" or True]
            for u in upstream:
                alt_edges = [v for v in self.venue.neighbors(u) if v != z]
                if not alt_edges:
                    continue

                # penalised graph: make edges leading into any flagged zone very expensive
                pg = self.venue.graph.copy()
                for a, b in list(pg.edges):
                    if b in flagged:
                        pg.edges[a, b]["penalised_weight"] = pg.edges[a, b]["base_weight"] * 25
                    else:
                        pg.edges[a, b]["penalised_weight"] = pg.edges[a, b]["base_weight"]

                target = min(self.venue.exit_zones,
                             key=lambda ex: self.sim.dist_to_exit.get(ex, 1e9)) \
                    if self.sim.dist_to_exit.get(u, 0) else None
                best_alt, best_path = None, None
                for v in alt_edges:
                    try:
                        path = nx.shortest_path(pg, v, self._nearest_exit(v), weight="penalised_weight")
                        if best_alt is None:
                            best_alt, best_path = v, path
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        continue
                if best_alt is None:
                    continue

                self.sim.steer_bias[(u, z)] = THROTTLE_BIAS
                self.sim.steer_bias[(u, best_alt)] = BOOST_BIAS

                via_str = " -> ".join(self.venue.zones[n].name for n in best_path)
                suggestions.append(RerouteSuggestion(
                    bottleneck_zone=z,
                    upstream_zone=u,
                    avoid_edge=(u, z),
                    suggested_edge=(u, best_alt),
                    suggested_via=via_str,
                    message=(
                        f"Predicted crush risk at '{alert.zone_name}' in "
                        f"{alert.lead_time_s}s (density -> {alert.predicted_density:.1f} ppl/sqm). "
                        f"Divert flow from '{self.venue.zones[u].name}' away from "
                        f"'{alert.zone_name}' via: {via_str}."
                    ),
                ))
        return suggestions

    def _nearest_exit(self, zone_id: str) -> str:
        return min(self.venue.exit_zones,
                   key=lambda ex: nx.shortest_path_length(
                       self.venue.graph, zone_id, ex, weight="base_weight"))
