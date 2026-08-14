from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging

from .core import DigitalTwin

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("grandprix")

# --- App ---
app = FastAPI(
    title="GrandPrix Crowd Digital Twin",
    version="1.0.0",
    description="Predictive crowd simulation, bottleneck forecasting and dynamic rerouting.",
)

# --- CORS (Restrict in production) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- State ---
twin = DigitalTwin()

# --- Schemas ---
class SensorUpdate(BaseModel):
    zones: dict[str, float] = Field(default_factory=dict)

class SpawnRequest(BaseModel):
    count: int = Field(default=25, ge=1, le=5000)

class StepRequest(BaseModel):
    seconds: float = Field(default=1.0, gt=0, le=60)

# --- Endpoints ---
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "grandprix-crowd-digital-twin",
        "version": "1.0.0",
    }

@app.get("/state")
def state():
    return twin.snapshot()

@app.post("/ingest")
def ingest(payload: SensorUpdate):
    logger.info(f"Ingesting {len(payload.zones)} zones")
    twin.ingest(payload.zones)
    return {"accepted_zones": len(payload.zones), "state": twin.snapshot()}

@app.post("/spawn")
def spawn(payload: SpawnRequest):
    created = twin.spawn(payload.count)
    logger.info(f"Spawned {created} agents")
    return {"requested": payload.count, "created": created, "state": twin.snapshot()}

@app.post("/step")
def step(payload: StepRequest):
    twin.step(payload.seconds)
    actions = twin.reroute()
    return {"reroutes": actions, "state": twin.snapshot()}

@app.get("/forecast")
def forecast():
    return {"horizon_minutes": 15, "forecast": twin.forecast(15)}

@app.post("/reroute")
def reroute():
    actions = twin.reroute()
    return {"actions": actions, "count": len(actions)}

@app.get("/graph")
def graph():
    return {
        "nodes": [vars(n) for n in twin.graph.nodes.values()],
        "edges": [vars(e) for (a, b), e in twin.graph.edges.items() if a < b],
    }

# --- Local Dev Only ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("grandprix.api:app", host="0.0.0.0", port=8001, reload=False)
