"""
scripts/run_demo.py
--------------------
Headless run of the digital twin - no browser needed. Useful as a fallback
demo path (if wifi/projector setup fails) and as a quick sanity check while
developing. Prints total occupancy every tick and any new alerts / reroute
actions as they fire.

Usage:
    python3 scripts/run_demo.py                 # runs the full scripted scenario
    python3 scripts/run_demo.py --ticks 60       # shorter run
    python3 scripts/run_demo.py --fast           # no wall-clock delay between ticks
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine import DigitalTwin  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=240, help="number of ticks to simulate (default 240 -> 40 sim-min at dt=10s)")
    ap.add_argument("--dt", type=int, default=10, help="simulated seconds per tick")
    ap.add_argument("--horizon", type=int, default=6, help="forecast horizon in ticks")
    ap.add_argument("--fast", action="store_true", help="don't sleep between ticks")
    args = ap.parse_args()

    twin = DigitalTwin(str(ROOT / "venue" / "venue_graph.json"), dt_s=args.dt, horizon_ticks=args.horizon)
    delay = 0.0 if args.fast else 0.05

    print(f"{'t(s)':>6} {'phase':<28} {'occupancy':>10}  status")
    seen_alert_zones: set[str] = set()

    for snap in twin.run_headless(args.ticks, wall_delay_s=delay):
        alerts = snap["alerts"]
        reroutes = snap["reroutes"]
        phase_name = ("EGRESS" if snap["phase"]["egress_intensity"] > 0.3 else
                      "RACE" if snap["phase"]["egress_intensity"] > 0 else
                      "ARRIVALS" if snap["phase"]["gate_inflow_ppl_per_min"] > 0 else "STEADY")

        status = ""
        new_zones = {a["zone_id"] for a in alerts} - seen_alert_zones
        if new_zones:
            for a in alerts:
                if a["zone_id"] in new_zones:
                    status += f"  ALERT: {a['zone_name']} -> {a['los_predicted']} in {a['lead_time_s']}s"
        seen_alert_zones = {a["zone_id"] for a in alerts}

        print(f"{snap['sim_time_s']:>6} {phase_name:<28} {snap['total_occupancy']:>10,}{status}")

        for r in reroutes:
            print(f"           -> REROUTE: {r['message']}")

    print("\nDone. Run `python3 server/app.py` for the live visual dashboard.")


if __name__ == "__main__":
    main()
