from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque
from heapq import heappop, heappush
from math import hypot
from typing import Dict, List, Tuple
import random


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
    """Small venue graph suitable for a hackathon digital-twin demo.

    Replace/extend this graph with a real venue map later; the simulation and
    routing APIs remain unchanged.
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

    def shortest_path(self, start: str, goal: str, density: Dict[str, float]) -> Tuple[List[str], float]:
        if start not in self.nodes or goal not in self.nodes:
            return [], float("inf")

        # W_e = L_e * [1 + alpha * (rho/rho_critical)^beta]
        alpha, beta, rho_critical = 2.0, 4.0, 3.5
        # Heap stores (f_score, g_score, node); keep A* priority separate
        # from g_score so stale-entry detection remains correct.
        pq = [(0.0, 0.0, start)]
        dist = {start: 0.0}
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
                new = cost + e.length * penalty * pressure
                if new < dist.get(v, float("inf")):
                    dist[v] = new
                    prev[v] = u
                    h = hypot(self.nodes[v].x - self.nodes[goal].x,
                              self.nodes[v].y - self.nodes[goal].y)
                    heappush(pq, (new + h, new, v))

        if goal not in prev:
            return [], float("inf")
        path = []
        cur: str | None = goal
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path, dist[goal]


class DigitalTwin:
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

    def _build_venue(self) -> VenueGraph:
        g = VenueGraph()
        # A compact motorsport/festival-style venue: gates -> concourse ->
        # grandstand/food zones -> multiple exits with a central choke point.
        coords = {
            "gate_a": (0, 4), "gate_b": (0, 10),
            "junction_w": (3, 7), "north": (6, 3), "south": (6, 12),
            "choke": (10, 7), "fan_zone": (13, 3), "food": (13, 11),
            "junction_e": (17, 7), "exit_a": (20, 3),
            "exit_b": (20, 7), "exit_c": (20, 12),
        }
        for node_id, (x, y) in coords.items():
            g.add_node(Node(node_id, x, y, 120 if "exit" in node_id else 80))
        links = [
            ("gate_a", "junction_w", 4.0), ("gate_b", "junction_w", 4.0),
            ("junction_w", "north", 5.0), ("junction_w", "south", 5.0),
            ("north", "choke", 6.0), ("south", "choke", 6.0),
            ("choke", "junction_e", 7.0), ("north", "fan_zone", 7.0),
            ("fan_zone", "junction_e", 5.0), ("south", "food", 7.0),
            ("food", "junction_e", 5.0), ("junction_e", "exit_a", 5.0),
            ("junction_e", "exit_b", 3.0), ("junction_e", "exit_c", 5.0),
        ]
        for a, b, length in links:
            g.add_edge(Edge(a, b, length, capacity=25.0 if "choke" in (a, b) else 40.0))
        return g

    def ingest(self, observations: Dict[str, float]) -> None:
        """Ingest camera/sensor aggregate counts (people per zone)."""
        for zone, count in observations.items():
            if zone not in self.density:
                continue
            self.density[zone] = max(0.0, float(count))
            self.history[zone].append(self.density[zone])

    def spawn(self, count: int = 20) -> int:
        starts = ["gate_a", "gate_b"]
        goals = ["exit_a", "exit_b", "exit_c"]
        for _ in range(max(0, count)):
            origin = random.choice(starts)
            goal = random.choice(goals)
            path, _ = self.graph.shortest_path(origin, goal, self.density)
            if not path:
                continue
            agent = Agent(self.next_agent_id, origin, goal, origin, path[1:])
            self.agents[agent.id] = agent
            self.next_agent_id += 1
        return count

    def step(self, seconds: float = 1.0) -> None:
        self.sim_time += seconds
        # Lightweight macroscopic flow model: move a bounded number of people
        # along each edge according to capacity and downstream pressure.
        for agent in list(self.agents.values()):
            if not agent.path:
                self.agents.pop(agent.id, None)
                continue
            nxt = agent.path[0]
            e = self.graph.edge(agent.node, nxt)
            flow = min(e.capacity * seconds / 10.0, max(1.0, self.density.get(agent.node, 0.0) * 0.05))
            if random.random() < min(1.0, flow / max(e.capacity, 1.0)):
                self.density[agent.node] = max(0.0, self.density[agent.node] - 1.0)
                self.density[nxt] += 1.0
                agent.node = nxt
                agent.path.pop(0)
                if agent.node == agent.goal:
                    self.agents.pop(agent.id, None)

        for zone in self.history:
            self.history[zone].append(self.density[zone])

    def forecast(self, horizon: int = 15) -> Dict[str, List[float]]:
        """Online trend forecast; no heavyweight model required for demo latency.

        Uses a robust EWMA + slope estimate over recent observations. This is
        intentionally transparent and can later be swapped for an LSTM/GBDT.
        """
        out: Dict[str, List[float]] = {}
        for zone, values in self.history.items():
            vals = list(values)
            if not vals:
                out[zone] = [self.density[zone]] * horizon
                continue
            recent = vals[-min(8, len(vals)):]
            level = recent[-1]
            slope = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
            preds = []
            for t in range(1, horizon + 1):
                # Damp slope to avoid unstable long-horizon extrapolation.
                preds.append(max(0.0, level + slope * t * 0.75))
            out[zone] = preds
        return out

    @staticmethod
    def risk(density: float) -> str:
        if density >= 3.5:
            return "EMERGENCY"
        if density >= 2.17:
            return "CRITICAL"
        if density >= 1.08:
            return "WARNING"
        return "NORMAL"

    def reroute(self) -> List[Dict]:
        forecast = self.forecast(15)
        effective = dict(self.density)
        for zone, values in forecast.items():
            if values:
                effective[zone] = max(effective.get(zone, 0.0), values[-1])

        risky = {z for z, d in effective.items() if d >= 1.08}
        actions = []
        for agent in self.agents.values():
            if not agent.path:
                continue
            if any(node in risky for node in agent.path[:4]):
                candidates = []
                for exit_id in ("exit_a", "exit_b", "exit_c"):
                    path, cost = self.graph.shortest_path(agent.node, exit_id, effective)
                    if path:
                        candidates.append((cost, exit_id, path))
                if candidates:
                    candidates.sort(key=lambda x: x[0])
                    _, target, path = candidates[0]
                    old = agent.path
                    agent.path = path[1:]
                    agent.goal = target
                    agent.rerouted = True
                    self.total_rerouted += 1
                    actions.append({
                        "agent_id": agent.id,
                        "from": old[0] if old else agent.node,
                        "target_exit": target,
                        "path": path,
                        "reason": "predicted_congestion",
                    })
        return actions

    def snapshot(self) -> Dict:
        forecasts = self.forecast(15)
        zones = []
        for zone, density in sorted(self.density.items()):
            predicted = max(forecasts[zone]) if forecasts[zone] else density
            zones.append({
                "zone": zone,
                "density": round(density, 3),
                "predicted_15m": round(predicted, 3),
                "risk": self.risk(predicted),
                "trend": "rising" if predicted > density + 0.05 else "stable",
            })
        return {
            "sim_time_sec": round(self.sim_time, 2),
            "active_agents": len(self.agents),
            "total_rerouted": self.total_rerouted,
            "zones": zones,
        }
