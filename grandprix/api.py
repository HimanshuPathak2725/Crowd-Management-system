from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .core import DigitalTwin


app = FastAPI(
    title="GrandPrix Crowd Digital Twin",
    version="1.0.0",
    description="Predictive crowd simulation, bottleneck forecasting and dynamic rerouting.",
)

twin = DigitalTwin()


class SensorUpdate(BaseModel):
    zones: dict[str, float] = Field(default_factory=dict)


class SpawnRequest(BaseModel):
    count: int = Field(default=25, ge=1, le=5000)


class StepRequest(BaseModel):
    seconds: float = Field(default=1.0, gt=0, le=60)


@app.get("/health")
def health():
    return {"status": "ok", "service": "grandprix-crowd-digital-twin"}


@app.get("/state")
def state():
    return twin.snapshot()


@app.post("/ingest")
def ingest(payload: SensorUpdate):
    twin.ingest(payload.zones)
    return {"accepted_zones": len(payload.zones), "state": twin.snapshot()}


@app.post("/spawn")
def spawn(payload: SpawnRequest):
    created = twin.spawn(payload.count)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("grandprix.api:app", host="127.0.0.1", port=8001, reload=True)
