# GrandPrix Crowd Digital Twin

This adds a self-contained predictive digital-twin layer to the existing
Crowd Management System.

## What changed

- Venue graph with gates, corridors, choke point, activity zones and exits.
- Capacity-aware, density-weighted A* routing.
- Macroscopic crowd-flow simulation.
- Online 15-step density forecast using a transparent EWMA + trend model.
- Bottleneck risk classification using Fruin-style density thresholds.
- Dynamic rerouting against predicted congestion.
- FastAPI endpoints for live sensor ingestion and dashboard integration.
- Automated tests for routing, forecasting and risk classification.

The implementation is deliberately dependency-light. Existing YOLO/OpenCV
modules can feed `/ingest` with zone-level counts. This means the CV layer and
the digital-twin layer remain decoupled: camera inference produces observations;
the twin turns observations into prediction + control decisions.

## Run

```bash
python -m pip install -r requirements-grandprix.txt
python -m grandprix.demo
python -m grandprix.api
```

API: `http://127.0.0.1:8001/docs`

## Sensor integration

POST:

```json
{
  "zones": {
    "gate_a": 45,
    "gate_b": 55,
    "choke": 115,
    "junction_e": 40,
    "exit_b": 12
  }
}
```

Then call `/forecast`, `/state`, or `/reroute`.

## Engineering boundary

This is a deterministic simulation/control layer, not a claim of
production-grade crowd safety certification. For a real venue, replace the
sample graph with a calibrated floorplan/occupancy graph, calibrate density
units from camera homography, validate forecasts against held-out event data,
and put operator approval around gate/signage actuation.
