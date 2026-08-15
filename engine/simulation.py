"""
simulation.py
--------------
A macroscopic ("digital twin") crowd simulator.

Why macroscopic instead of per-agent?
At venue scale (tens of thousands of people) a full agent-based / social-force
simulation is too expensive to run in real time and doesn't add forecasting
value over a well-known, empirically validated alternative: the
**Cell Transmission Model** (Daganzo, 1994), adapted here from vehicle traffic
to pedestrian flow. Each zone is a "cell" holding an occupancy count; each
walkway is a channel with a sending/receiving capacity. This is the same
family of model used by real venue-safety consultancies (see Fruin's Level
of Service framework, referenced in venue_graph.json's LOS thresholds).

Two effects are modelled explicitly because they are what actually cause
real-world crushes and are the whole point of forecasting them:
  1. Discharge collapse: a zone's own outflow rate drops as its density
     approaches "crush" density (the empirically observed "faster is slower"
     effect in pedestrian dynamics).
  2. Receiving-capacity throttling: a corridor cannot push more people into
     a zone than that zone has room to receive, so congestion backs upstream
     exactly like a traffic jam - which is what lets us *forecast* it a
     few ticks before it becomes dangerous.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .venue import Venue


@dataclass
class ArrivalPhase:
    """One scripted phase of the demo scenario (sim-seconds are simulation time,
    not wall-clock time - see orchestrator.py for the wall-clock speed-up)."""
    start_s: int
    end_s: int
    gate_inflow_ppl_per_min: float   # combined arrival rate at gate_a + gate_b
    egress_intensity: float          # 0..1, fraction of viewing-zone occupants/tick trying to leave


DEFAULT_SCENARIO: list[ArrivalPhase] = [
    ArrivalPhase(0,    900,  gate_inflow_ppl_per_min=1400, egress_intensity=0.00),  # gates open / fans arrive
    ArrivalPhase(900,  1500, gate_inflow_ppl_per_min=300,  egress_intensity=0.02),  # race running, light amenity churn
    ArrivalPhase(1500, 2400, gate_inflow_ppl_per_min=0,    egress_intensity=0.55),  # chequered flag -> mass egress
]


def scenario_phase(sim_time_s: int, scenario: list[ArrivalPhase] = DEFAULT_SCENARIO) -> ArrivalPhase:
    for phase in scenario:
        if phase.start_s <= sim_time_s < phase.end_s:
            return phase
    return scenario[-1]


# One-way ingress progression: fans always move deeper into the venue
# (gate -> concourse -> amenity -> viewing), mirroring the one-way turnstile
# / concourse design used in real stadiums so people don't churn back and
# forth. Egress mode uses dist_to_exit instead (computed per-venue below).
ZONE_RANK = {"entry": 0, "concourse": 1, "amenity": 2, "viewing": 3, "exit": 4}


class CrowdSimulation:
    def __init__(self, venue: Venue, dt_s: int = 10, scenario: list[ArrivalPhase] | None = None):
        self.venue = venue
        self.dt_s = dt_s
        self.scenario = scenario or DEFAULT_SCENARIO
        self.sim_time_s = 0
        # precompute static shortest-path distance from every zone to its nearest exit
        self.dist_to_exit = self._compute_dist_to_exit()
        # per-edge steering bias the rerouting engine can adjust: (u, v) -> multiplier
        self.steer_bias: dict[tuple[str, str], float] = {}

    def _compute_dist_to_exit(self) -> dict[str, float]:
        import networkx as nx
        dist = {}
        for zid in self.venue.zones:
            best = math.inf
            for ex in self.venue.exit_zones:
                try:
                    d = nx.shortest_path_length(self.venue.graph, zid, ex, weight="base_weight")
                    best = min(best, d)
                except nx.NetworkXNoPath:
                    continue
            dist[zid] = best
        return dist

    # ---- discharge (outflow) capacity of a zone, with congestion collapse ----
    def _discharge_rate_ppl_per_min(self, zone_id: str) -> float:
        z = self.venue.zones[zone_id]
        t = self.venue.los_thresholds
        free_flow = z.area_sqm * 1.2          # ppl/min able to approach an exit when uncongested
        d = z.density
        if d <= t["congested"]:
            factor = 1.0
        elif d >= t["crush_risk"]:
            factor = 0.15                      # near-total discharge collapse at crush density
        else:
            span = t["crush_risk"] - t["congested"]
            factor = 1.0 - 0.85 * (d - t["congested"]) / span
        return free_flow * factor

    def _receiving_room(self, zone_id: str) -> int:
        z = self.venue.zones[zone_id]
        return max(0, z.capacity - z.occupancy)

    def _out_edge_weight(self, u: str, v: str, mode: str) -> float:
        """Attractiveness of edge u->v for routing purposes (higher = more preferred)."""
        edata = self.venue.graph.edges[u, v]
        vzone = self.venue.zones[v]
        bias = self.steer_bias.get((u, v), 1.0)

        if mode == "egress":
            # only ever move towards (or level with) the nearest exit
            if self.dist_to_exit[v] > self.dist_to_exit[u] + 1e-6:
                return 0.0
        else:  # ingress
            if vzone.type in ("exit", "entry"):
                return 0.0  # don't send freshly-arrived fans straight out an exit / back to the gate
            u_rank, v_rank = ZONE_RANK[self.venue.zones[u].type], ZONE_RANK[vzone.type]
            forward = v_rank > u_rank or (v_rank == u_rank and vzone.type == "amenity")
            if not forward:
                return 0.0  # one-way progression only - no backward churn towards the gates

        congestion_penalty = 1.0 + 3.0 * vzone.density / max(self.venue.los_thresholds["at_risk"], 0.1)
        room_factor = max(self._receiving_room(v), 1)
        return bias * edata["capacity_ppl_per_min"] * room_factor / congestion_penalty

    def _route_split(self, u: str, mode: str) -> dict[str, float]:
        neighbors = self.venue.neighbors(u)
        weights = {v: self._out_edge_weight(u, v, mode) for v in neighbors}
        total = sum(weights.values())
        if total <= 0:
            return {}
        return {v: w / total for v, w in weights.items() if w > 0}

    def step(self) -> None:
        """Advance the simulation by one tick (dt_s simulated seconds)."""
        phase = scenario_phase(self.sim_time_s, self.scenario)
        dt_min = self.dt_s / 60.0

        pending_out: dict[str, float] = {zid: 0.0 for zid in self.venue.zones}
        pending_in: dict[str, float] = {zid: 0.0 for zid in self.venue.zones}

        for zid, zone in self.venue.zones.items():
            if zone.type in ("entry",):
                continue  # entries don't discharge via the graph logic, they just inject below

            # decide whether this zone is currently acting in "egress" or "ingress" routing mode
            if zone.type == "viewing":
                # grandstands/paddock are pure sinks until egress actually begins -
                # fans watching the race don't wander back out through the concourse
                if phase.egress_intensity <= 0:
                    continue
                mode, intensity = "egress", phase.egress_intensity
            elif zone.type == "amenity":
                mode = "egress" if phase.egress_intensity > 0 else "ingress"
                intensity = phase.egress_intensity if mode == "egress" else 1.0
            elif zone.type == "exit":
                # exits are the physical gate/turnstile bottleneck: people here leave the
                # venue entirely (removed from the simulated system), throttled by the
                # same congestion-collapse curve as any other discharge - a packed exit
                # gate genuinely processes people slower, which is exactly the failure
                # mode this whole system exists to forecast and relieve in advance.
                if zone.occupancy <= 0:
                    continue
                left_venue = min(zone.occupancy, self._discharge_rate_ppl_per_min(zid) * dt_min)
                pending_out[zid] += left_venue
                continue
            else:  # concourse
                mode = "egress" if phase.egress_intensity > 0.3 else "ingress"
                intensity = 1.0

            if zone.occupancy <= 0:
                continue

            max_discharge = self._discharge_rate_ppl_per_min(zid) * dt_min
            desired_out = min(zone.occupancy * (intensity if mode == "egress" else 1.0), max_discharge)
            if desired_out <= 0:
                continue

            split = self._route_split(zid, mode)
            if not split:
                continue

            for v, frac in split.items():
                edge = self.venue.graph.edges[zid, v]
                proposed = desired_out * frac
                edge_cap = edge["capacity_ppl_per_min"] * dt_min
                room = self._receiving_room(v)
                actual = max(0.0, min(proposed, edge_cap, room - pending_in[v]))
                edge["flow"] = actual / dt_min if dt_min else 0.0
                pending_out[zid] += actual
                pending_in[v] += actual

        # apply moves
        for zid, zone in self.venue.zones.items():
            zone.occupancy = max(0, zone.occupancy - int(pending_out[zid]) + int(pending_in[zid]))

        # exogenous arrivals at the gates
        if phase.gate_inflow_ppl_per_min > 0 and self.venue.entry_zones:
            per_gate = phase.gate_inflow_ppl_per_min * dt_min / len(self.venue.entry_zones)
            for gid in self.venue.entry_zones:
                gzone = self.venue.zones[gid]
                room = self._receiving_room(gid)
                gzone.occupancy += int(min(per_gate, room))
                # gate itself immediately tries to push people onward to the concourse
                split = self._route_split(gid, "ingress")
                for v, frac in split.items():
                    edge = self.venue.graph.edges[gid, v]
                    edge_cap = edge["capacity_ppl_per_min"] * dt_min
                    room_v = self._receiving_room(v)
                    move = int(min(gzone.occupancy * frac, edge_cap, room_v))
                    gzone.occupancy -= move
                    self.venue.zones[v].occupancy += move

        self.sim_time_s += self.dt_s

    def snapshot(self) -> dict:
        return {
            "sim_time_s": self.sim_time_s,
            "phase": scenario_phase(self.sim_time_s, self.scenario).__dict__,
            "zones": {
                zid: {
                    "occupancy": z.occupancy,
                    "capacity": z.capacity,
                    "density": round(z.density, 3),
                    "los": self.venue.los_level(z.density),
                }
                for zid, z in self.venue.zones.items()
            },
            "total_occupancy": self.venue.total_occupancy(),
        }
