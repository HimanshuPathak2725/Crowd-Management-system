"""CLI demo: run the digital twin without a camera or GPU."""
from .core import DigitalTwin


def main():
    twin = DigitalTwin()
    twin.ingest({
        "gate_a": 45, "gate_b": 55, "junction_w": 30,
        "north": 22, "south": 28, "choke": 115,
        "fan_zone": 18, "food": 20, "junction_e": 40,
        "exit_a": 8, "exit_b": 12, "exit_c": 10,
    })
    twin.spawn(120)

    for _ in range(20):
        twin.step(5)
        actions = twin.reroute()
        snap = twin.snapshot()
        worst = sorted(snap["zones"], key=lambda z: z["predicted_15m"], reverse=True)[:3]
        print(
            f"t={snap['sim_time_sec']:5.1f}s "
            f"agents={snap['active_agents']:3d} "
            f"rerouted={snap['total_rerouted']:3d} "
            f"worst={[(z['zone'], z['risk'], z['predicted_15m']) for z in worst]}"
        )
        if actions:
            print(f"  -> {len(actions)} dynamic reroutes")


if __name__ == "__main__":
    main()
