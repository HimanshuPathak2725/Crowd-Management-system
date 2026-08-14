from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque
from heapq import heappop, heappush
from math import hypot
from typing import Dict, List, Tuple
import logging
import random

logger = logging.getLogger(__name__)

__all__ = ["Node", "Edge", "Agent", "VenueGraph", "DigitalTwin"]


@dataclass(frozen=True)
class Node:
    id: str
    x: float
    y: float
    capacity: float = 80.0


@dataclass(frozen=True)
class Edge:
    a: str
    b: str
    length: float
    capacity: float = 25.0


@dataclass
class Agent:
    id: int
    origin: str
    goal: str
    node: str
    path: List[str] = field(default_factory=list)
    rerouted: bool = False


class VenueGraph:
    """Graph-based venue digital twin for crowd flow simulation.

    Replace/extend this graph with a real venue map (JSON/YAML import);
    the simulation and routing APIs remain unchanged.
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[Tuple[str, str], Edge] = {}
        self.adj: Dict[str, List[str]] = {}

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node
        self.adj.setdefault(node.id, [])

    def add_edge(self, edge: Edge) -> None:
        self.edges[(edge.a, edge.b)] = edge
        self.edges[(edge.b, edge.a)] = Edge(edge.b, edge.a, edge.length, edge.capacity)
        self.adj.setdefault(edge.a, []).append(edge.b)
        self.adj.setdefault(edge.b, []).append(edge.a)

    def edge(self, a: str, b: str) -> Edge:
        return self.edges[(a, b)]

    def shortest_path(
        self, start: str, goal: str, density: Dict[str, float]
    ) -> Tuple[List[str], float]:
        """Density-weighted A* routing."""
        if start not in self.nodes or goal not in self.nodes:
            return [], float("inf")

        # W_e = L_e * [1 + alpha * (rho / rho_critical)^beta]
        alpha, beta, rho_critical = 2.0, 4.0, 3.5
        pq = [(0.0, 0.0, start)]
        dist: Dict[str, float] = {start: 0.0}
        prev: Dict[str, str | None] = {start: None}

        while pq:
            _, cost, u = heappop(pq)
            if cost != dist[u]:
                continue
            if u == goal:
                break
            for v in self.adj.get(u, []):
                e = self.edge(u, v)
                rho = max(0.0, density.get(v, 0.0))
                penalty = 1.0 + alpha * min(rho / rho_critical, 2.0) ** beta
                # Capacity pressure adds a second operational signal.
                load = density.get(v, 0.0) / max(self.nodes[v].capacity / 100.0, 0.1)
                pressure = 1.0 + min(max(load, 0.0), 3.0) * 0.15
                new_cost = cost + e.length * penalty * pressure
                if new_cost < dist.get(v, float("inf")):
                    dist[v] = new_cost
                    prev[v] = u
                    h = hypot(
                        self.nodes[v].x - self.nodes[goal].x,
                        self.nodes[v].y - self.nodes[goal].y,
                    )
                    heappush(pq, (new_cost + h, new_cost, v))

        if goal not in prev:
            return [], float("inf")
        path: List[str] = []
        cur: str | None = goal
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path, dist[goal]


class DigitalTwin:
    """Predictive crowd digital twin with simulation, forecasting & rerouting."""

    def __init__(self, seed: int = 42) -> None:
        random.seed(seed)
        self.graph = self._build_venue()
        self.density: Dict[str, float] = {n: 0.0 for n in self.graph.nodes}
        self.history: Dict[str, deque[float]] = {
            n: deque(maxlen=30) for n in self.graph.nodes
        }
        self.agents: Dict[int, Agent] = {}
        self.next_agent_id = 1
        self.sim_time = 0.0
        self.total_rerouted = 0
        self._forecaster = None

    # ------------------------------------------------------------------
    # HF Forecaster (optional — loads lazily)
    # ------------------------------------------------------------------
    @property
    def forecaster(self):
        if self._forecaster is None:
            try:
                from .forecasting import HFForecaster

                self._forecaster = HFForecaster()
                logger.info("Hugging Face forecaster loaded")
            except Exception as exc:
                logger.warning("HF forecaster unavailable, using statistical fallback: %s", exc)
                self._forecaster = False  # sentinel: tried and failed
        return self._forecaster

    # ------------------------------------------------------------------
    # Venue builder
    # ------------------------------------------------------------------
    def _build_venue(self) -> VenueGraph:
        g = VenueGraph()
        # A compact motorsport/festival-style venue.
        coords = {
            "gate_a": (0, 4),
            "gate_b": (0, 10),
            "junction_w": (3, 7),
            "north": (6, 3),
            "south": (6, 12),
            "choke": (10, 7),
            "fan_zone": (13, 3),
            "food": (13, 11),
            "junction_e": (17, 7),
            "exit_a": (20, 3),
            "exit_b": (20, 7),
            "exit_c": (20, 12),
        }
        for node_id, (x, y) in coords.items():
            cap = 120.0 if "exit" in node_id else 80.0
            g.add_node(Node(node_id, x, y, cap))

        links = [
            ("gate_a", "junction_w", 4.0),
            ("gate_b", "junction_w", 4.0),
            ("junction_w", "north", 5.0),
            ("junction_w", "south", 5.0),
            ("north", "choke", 6.0),
            ("south", "choke", 6.0),
            ("choke", "junction_e", 7.0),
            ("north", "fan_zone", 7.0),
            ("fan_zone", "junction_e", 5.0),
            ("south", "food", 7.0),
            ("food", "junction_e", 5.0),
            ("junction_e", "exit_a", 5.0),
            ("junction_e", "exit_b", 3.0),
            ("junction_e", "exit_c", 5.0),
        ]
        for a, b, length in links:
            cap = 25.0 if "choke" in (a, b) else 40.0
            g.add_edge(Edge(a, b, length, cap))
        return g

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def ingest(self, observations: Dict[str, float]) -> None:
        """Ingest camera/sensor aggregate counts (people per zone)."""
        for zone, count in observations.items():
            if zone not in self.density:
                logger.warning("Unknown zone '%s' ignored", zone)
                continue
            self.density[zone] = max(0.0, float(count))
            self.history[zone].append(self.density[zone])

    def spawn(self, count: int = 20) -> int:
        """Spawn agents at entry gates bound for random exits."""
        starts = ["gate_a", "gate_b"]
        goals = ["exit_a", "exit_b", "exit_c"]
        created = 0
        for _ in range(max(0, count)):
            origin = random.choice(starts)
            goal = random.choice(goals)
            path, _ = self.graph.shortest_path(origin, goal, self.density)
            if not path:
                continue
            agent = Agent(self.next_agent_id, origin, goal, origin, path[1:])
            self.agents[agent.id] = agent
            self.next_agent_id += 1
            created += 1
        logger.info("Spawned %d/%d agents", created, count)
        return created  # FIXED: was returning `count`

    def step(self, seconds: float = 1.0) -> None:
        """Advance simulation by `seconds`."""
        self.sim_time += seconds

        # Macroscopic flow: probabilistic movement bounded by edge capacity.
        for agent in list(self.agents.values()):
            if not agent.path:
                self.agents.pop(agent.id, None)
                continue

            nxt = agent.path[0]
            e = self.graph.edge(agent.node, nxt)

            flow = min(
                e.capacity * seconds / 10.0,
                max(1.0, self.density.get(agent.node, 0.0) * 0.05),
            )
            move_prob = min(1.0, flow / max(e.capacity, 1.0))

            if random.random() < move_prob:
                # FIXED: proper indentation + capacity capping
                self.density[agent.node] = max(
                    0.0, self.density[agent.node] - 1.0
                )
                self.density[nxt] = min(
                    self.graph.nodes[nxt].capacity,
                    self.density.get(nxt, 0.0) + 1.0,
                )

                agent.node = nxt
                agent.path.pop(0)
                if agent.node == agent.goal:
                    self.agents.pop(agent.id, None)

        # Record history
        for zone in self.history:
            self.history[zone].append(self.density[zone])

    def forecast(self, horizon: int = 15) -> Dict[str, List[float]]:
        """Predict future density per zone.

        Tries Hugging Face forecaster first, falls back to EWMA + trend.
        """
        out: Dict[str, List[float]] = {}

        # Attempt HF if available
        hf = self.forecaster
        if hf and hf is not False:
            try:
                for zone, values in self.history.items():
                    hist = list(values)
                    if len(hist) >= 8:
                        out[zone] = hf.predict(hist, horizon)
                    else:
                        out[zone] = self._statistical_predict(hist, horizon)
                return out
            except Exception as exc:
                logger.error("HF forecast failed: %s", exc)

        # Statistical fallback
        for zone, values in self.history.items():
            out[zone] = self._statistical_predict(list(values), horizon)
        return out

    @staticmethod
    def _statistical_predict(history: List[float], horizon: int) -> List[float]:
        if not history:
            return [0.0] * horizon
        recent = history[-min(8, len(history)) :]
        level = recent[-1]
        slope = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
        return [max(0.0, level + slope * t * 0.75) for t in range(1, horizon + 1)]

    @staticmethod
    def risk(density: float, capacity: float = 80.0) -> str:
        """Classify risk using capacity-relative thresholds (Fruin-style)."""
        ratio = density / max(capacity, 1.0)
        if ratio >= 0.80:
            return "EMERGENCY"
        if ratio >= 0.50:
            return "CRITICAL"
        if ratio >= 0.25:
            return "WARNING"
        return "NORMAL"

    def reroute(self) -> List[Dict]:
        """Dynamically reroute agents away from predicted congestion."""
        forecast = self.forecast(15)
        effective = dict(self.density)
        for zone, values in forecast.items():
            if values:
                effective[zone] = max(effective.get(zone, 0.0), values[-1])

        risky = {z for z, d in effective.items() if self.risk(d, self.graph.nodes[z].capacity) != "NORMAL"}
        actions: List[Dict] = []

        for agent in self.agents.values():
            if not agent.path:
                continue
            # Only reroute if agent is heading into a risky zone soon
            if not any(node in risky for node in agent.path[:4]):
                continue

            candidates = []
            for exit_id in ("exit_a", "exit_b", "exit_c"):
                path, cost = self.graph.shortest_path(agent.node, exit_id, effective)
                if path:
                    candidates.append((cost, exit_id, path))

            if not candidates:
                continue

            candidates.sort(key=lambda x: x[0])
            _, target, path = candidates[0]

            # Don't reroute if current path is already the best option
            if target == agent.goal and len(path) >= len(agent.path):
                continue

            old = agent.path
            agent.path = path[1:]
            agent.goal = target
            agent.rerouted = True
            self.total_rerouted += 1

            actions.append(
                {
                    "agent_id": agent.id,
                    "from": old[0] if old else agent.node,
                    "target_exit": target,
                    "path": path,
                    "reason": "predicted_congestion",
                }
            )

        if actions:
            logger.info("Rerouted %d agents", len(actions))
        return actions

    def snapshot(self) -> Dict:
        """Current system state for dashboards / APIs."""
        forecasts = self.forecast(15)
        zones = []
        for zone, density in sorted(self.density.items()):
            predicted = max(forecasts[zone]) if forecasts.get(zone) else density
            cap = self.graph.nodes[zone].capacity
            zones.append(
                {
                    "zone": zone,
                    "density": round(density, 3),
                    "capacity": cap,
                    "predicted_15m": round(predicted, 3),
                    "risk": self.risk(predicted, cap),
                    "trend": (
                        "rising"
                        if predicted > density + 0.05
                        else "falling"
                        if predicted < density - 0.05
                        else "stable"
                    ),
                }
            )
        return {
            "sim_time_sec": round(self.sim_time, 2),
            "active_agents": len(self.agents),
            "total_rerouted": self.total_rerouted,
            "zones": zones,
        }

    def reset(self) -> None:
        """Reset simulation state (useful for testing / new events)."""
        self.density = {n: 0.0 for n in self.graph.nodes}
        self.history = {n: deque(maxlen=30) for n in self.graph.nodes}
        self.agents.clear()
        self.next_agent_id = 1
        self.sim_time = 0.0
        self.total_rerouted = 0
        logger.info("DigitalTwin reset")
