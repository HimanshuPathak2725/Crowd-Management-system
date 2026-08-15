# Live GrandPrix Crowd Digital Twin

This layer adds the live, browser-based digital twin from the validated
`crowd-digital-twin` prototype without deleting the existing CV modules.

## Run tests

```bash
python3 -m unittest discover -s tests -v
```

Expected result:

```text
Ran 6 tests ... OK
```

## Run the live dashboard

```bash
python3 -m pip install -r requirements-grandprix-live.txt
python3 server/app.py
```

Open:

```text
http://localhost:8000
```

The server is intentionally implemented with Python's standard-library
`http.server`, so the dashboard has no external CDN dependency.

## Headless fallback

```bash
python3 scripts/run_demo.py --fast
```

## Architecture

```text
Venue graph
    ↓
Cell Transmission crowd simulation
    ↓
Online per-zone SGDRegressor forecasting
    ↓
Fruin LOS bottleneck detection
    ↓
Dijkstra-based dynamic rerouting
    ↓
Live browser dashboard
```

The venue graph is synthetic and designed for a Grand Prix-style spectator
venue. Replace `venue/venue_graph.json` with a calibrated event layout when
real venue geometry and capacities are available.

The simulation is macroscopic rather than agent-based: each zone tracks
occupancy and each walkway has sending/receiving capacity. This is deliberate
for real-time venue-scale simulation.

The forecasting model is online and incrementally trained on the simulated
density stream. It is a transparent hackathon baseline, not a claim of a
production safety-certified predictor.

## Demo story

1. Gates open and spectators enter.
2. Crowd accumulates in concourses and viewing areas.
3. Race ends and mass egress begins.
4. Forecasting detects future congestion before the zone reaches the risk
   threshold.
5. The rerouting engine throttles risky edges and boosts alternatives.
6. The dashboard shows the bottleneck, lead time, and reroute action.
7. Exit discharge drains the venue instead of allowing occupancy to remain
   permanently stuck inside exit zones.
