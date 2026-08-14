# 🏁 F1 Stadium Crowd Flow Optimiser

> **Real-time crowd simulation, bottleneck forecasting, and dynamic rerouting for large venues.**

An AI-assisted crowd management system designed for stadiums, motorsport venues, festivals, railway stations, and other high-density public events.

The project combines **computer vision**, **crowd-density analysis**, a **venue digital twin**, **capacity-aware crowd simulation**, **bottleneck forecasting**, and **dynamic route optimisation** to help event operators identify dangerous crowd build-ups *before* they become critical and guide people toward safer, less congested paths.

> **Hackathon Problem Statement:** Crowd Flow Optimiser — *Simulating and rerouting crowds in real time.*

---

## 🎯 Problem

Large venues can develop dangerous crowd concentrations around:

- Entry and exit gates
- Narrow walkways and choke points
- Food/concession areas
- Junctions
- Grandstands and spectator zones
- Emergency exits

Traditional monitoring is mostly reactive: an operator sees that an area is already crowded and then responds.

The goal of this project is to move from:

```text
"Where is the crowd right now?"

to:

"Where is the crowd likely to become dangerous,
when will it happen, and what should we do now?"


---

💡 What We Build

The system is designed around a closed-loop crowd-management pipeline:

┌───────────────────────┐
│ CCTV / Video Streams  │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ YOLOv8 Person         │
│ Detection + Tracking  │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Crowd / Zone          │
│ Aggregation           │
└───────────┬───────────┘
            │
            ▼
┌────────────────────────────────┐
│       VENUE DIGITAL TWIN       │
│                                │
│ Zones + Walkways + Capacities  │
│ + Crowd Simulation             │
└───────────────┬────────────────┘
                │
        ┌───────┴────────┐
        ▼                ▼
┌──────────────┐  ┌───────────────┐
│ Forecasting  │  │ Bottleneck /  │
│ T+5/T+10/T+15│  │ Risk Engine   │
└──────┬───────┘  └───────┬───────┘
       └──────────┬───────┘
                  ▼
        ┌────────────────────┐
        │ Dynamic Route      │
        │ Optimisation       │
        └─────────┬──────────┘
                  ▼
      ┌───────────────────────────┐
      │ Operator Dashboard /      │
      │ Recommended Rerouting     │
      └───────────────────────────┘


---

🚀 Current Capabilities

The repository contains two layers.

1. Existing Computer-Vision Modules

The original project provides:

👥 Real-time person detection

🎯 YOLOv8-based tracking

📊 Crowd counting

🔥 Grid-based density mapping

🚨 Crowd threshold alerts

🧭 Multi-route crowd analysis

🛣 Route recommendation

🔊 Voice guidance

📈 Interactive visualisations

📹 CCTV/video analysis

🧠 Crowd movement / behaviour analysis


2. GrandPrix Crowd Intelligence Engine

The new grandprix/ package adds the predictive and simulation layer:

🗺️ Venue graph / digital-twin representation

👥 Capacity-aware crowd simulation

📈 Online density forecasting

🚨 Bottleneck risk classification

🧭 Density-aware A* routing

🔀 Dynamic rerouting

🌐 FastAPI control plane

🧪 Automated tests

🎮 Reproducible simulation demo



---

🧠 GrandPrix Engine

The core engine lives in:

grandprix/
├── __init__.py
├── core.py       # Digital twin, simulation, forecasting, routing
├── api.py        # FastAPI interface
└── demo.py       # End-to-end simulation demo


---

🗺️ Digital Twin

The venue is represented as a graph:

North
                   │
             ┌─────┴─────┐
             │           │
          Junction W   Junction E
             │           │
Gate A ──────┤           ├────── Gate B
             │           │
             └─────┬─────┘
                   │
                Choke
                   │
                 Exit

Each zone/node can carry information such as:

Capacity

Current population

Predicted population

Risk level


Walkways/edges carry information such as:

Distance

Capacity

Travel cost

Congestion pressure


This allows the physical venue to be represented as a computational model that can be simulated and optimised.


---

🔮 Bottleneck Forecasting

Instead of only reacting to current crowd density, the engine projects future density from recent observations.

The current prototype uses a lightweight and interpretable forecasting approach based on:

Exponentially weighted density history

Recent trend

Capacity-aware risk thresholds


The forecasting interface is intentionally modular so a stronger learned model can replace the baseline without changing the rest of the system.

Future model candidates include:

XGBoost / LightGBM

Temporal regression

LSTM / GRU

Temporal Transformers



---

🚨 Bottleneck Detection

Predicted density is converted into operational risk levels:

NORMAL
   ↓
WARNING
   ↓
CRITICAL
   ↓
EMERGENCY

The system ranks the most problematic zones so operators can focus on the areas that need intervention first.

Example:

Zone             Predicted Risk
────────────────────────────────
Main Choke       EMERGENCY
West Junction    CRITICAL
Gate B           WARNING
North Corridor   NORMAL


---

🧭 Dynamic Rerouting

The routing engine does not simply choose the shortest path.

It considers:

Travel distance
       +
Current congestion
       +
Capacity pressure
       +
Predicted crowding

Therefore, a slightly longer path can become preferable when the shortest path is heavily congested.

┌─────────────┐
                 │ Destination │
                 └──────┬──────┘
                        │
              ┌─────────┴─────────┐
              │                   │
        Short route          Alternate route
        HIGH congestion      LOW congestion
              │                   │
              ▼                   ▼
        Higher cost           Lower cost
                                  │
                                  ▼
                         Recommended route


---

🎥 Existing Computer Vision Pipeline

The repository already contains several CV-oriented modules.

Crowd Behaviour Analysis

Provides:

Person detection

Tracking

Movement analysis

Speed estimation

Direction analysis

Trajectory visualisation

Crowd-flow monitoring


Crowd Alert System

Provides:

Real-time crowd counting

Configurable thresholds

Automatic alerts

Live monitoring


Crowd Density Mapper

Provides:

Spatial density estimation

Heatmaps

Grid-based zone analysis

Low/medium/high density visualisation


Temple Crowd Lane Management

Provides:

Multi-route analysis

Crowd estimation

Travel-time estimation

Route recommendation

Voice guidance


> These modules form the computer-vision foundation. The grandprix/ engine adds the venue-level simulation, prediction, and routing layer required by the Crowd Flow Optimiser problem.




---

🌐 API

The GrandPrix engine exposes a FastAPI control plane.

Method	Endpoint	Purpose

GET	/health	Health check
GET	/state	Current digital-twin state
POST	/ingest	Ingest crowd observations
POST	/spawn	Add simulated crowd
POST	/step	Advance simulation
GET	/forecast	Retrieve predicted density
POST	/reroute	Calculate rerouting
GET	/graph	Inspect venue graph


Interactive API documentation is available through FastAPI/Swagger.


---

⚙️ Installation

1. Clone the repository

git clone https://github.com/HimanshuPathak2725/Crowd-Management-system.git
cd Crowd-Management-system

2. Create a virtual environment

python3 -m venv .venv
source .venv/bin/activate

3. Install GrandPrix engine dependencies

pip install -r requirements-grandprix.txt

> The original computer-vision modules may have additional dependencies depending on which module you run.




---

▶️ Run the GrandPrix Simulation

python -m grandprix.demo

The demo simulates crowd movement through the venue and continuously reports:

Simulation time

Active agents

Predicted bottlenecks

Risk levels

Dynamic rerouting decisions


Example:

t=  5.0s agents=120 rerouted=120
worst=[('choke', 'EMERGENCY', ...)]

→ 120 dynamic reroutes


---

🌐 Run the API

python -m grandprix.api

Then open:

http://127.0.0.1:8001/docs


---

🧪 Testing

The GrandPrix engine includes automated tests.

Run:

python -m pytest -q

Current baseline:

3 passed


---

📊 System Workflow

The intended end-to-end workflow is:

Step 1 — Observe

CCTV/video feeds provide people detections and movement information.

Step 2 — Localise

Detections are mapped into venue zones.

Step 3 — Aggregate

The system calculates:

People per zone

Density

Flow

Direction

Recent trend


Step 4 — Simulate

The digital twin models how people move through the venue graph.

Step 5 — Predict

The forecasting layer estimates future crowd pressure.

Step 6 — Detect

The system identifies zones likely to become bottlenecks.

Step 7 — Optimise

Density-aware routing calculates safer alternatives.

Step 8 — Act

The system produces recommended rerouting decisions for operators and, eventually, digital signage/guidance systems.


---

🏆 Why This Approach?

Many basic crowd-management systems stop at:

Detect people
     ↓
Count people
     ↓
Raise alert

This project aims to close the loop:

Detect
  ↓
Understand
  ↓
Simulate
  ↓
Predict
  ↓
Optimise
  ↓
Reroute
  ↓
Measure outcome

That changes the system from a reactive monitoring tool into a predictive crowd-flow optimisation platform.


---

🏁 Example F1 Scenario

Imagine thousands of spectators leaving a grandstand immediately after an F1 race.

Grandstand
    │
    ▼
Junction
    │
    ▼
Choke Point ─────── Exit A
    │
    └─────────────── Exit B

The system detects rising inflow toward the choke point.

Without intervention

Density
  ↑
  │                ███████
  │          █████████████
  │    ███████████████████
  └────────────────────────→ Time

             🚨 CRITICAL

With prediction + rerouting

The system predicts the bottleneck early and diverts part of the incoming crowd toward Exit B.

Incoming Crowd
       │
       ├──────────► Exit A
       │
       └──────────► Exit B
                    ↑
              Dynamic routing

The objective is to reduce peak density, distribute crowd flow, and prevent the bottleneck from becoming dangerous.


---

🔬 Planned Hackathon Enhancements

The current engine is the foundation. The next development stages are:

Phase 1 — Real CV → Digital Twin Integration

YOLO Tracking
      ↓
Camera calibration / homography
      ↓
Venue coordinates
      ↓
Zone-level crowd state
      ↓
Digital Twin

Phase 2 — Stronger Forecasting

Add multi-step forecasting for:

T+5 min
T+10 min
T+15 min

with uncertainty/confidence estimates.

Phase 3 — Smarter Rerouting

Add:

Rerouting hysteresis

Route-change cooldowns

Flow balancing

Exit capacity constraints

Predicted rather than only current congestion


Phase 4 — Command Centre

Build a unified dashboard containing:

Live venue digital twin

Crowd heatmap

Bottleneck alerts

Forecast timeline

Recommended routes

System KPIs


Phase 5 — What-if Simulation

Allow operators to test:

+1000 arriving people
Gate closure
Emergency at zone X
Unexpected crowd surge

and compare outcomes before taking action.

Phase 6 — Emergency Evacuation

Support emergency mode with:

Safe-exit selection

Incoming-flow suppression

Evacuation route optimisation

Capacity-aware exit distribution



---

📈 Evaluation Metrics

The system should ultimately be evaluated using measurable outcomes:

Metric	Goal

Peak zone density	↓
Average travel time	↓
Critical bottleneck duration	↓
Prediction MAE	↓
Bottleneck warning lead time	↑
Successful reroutes	↑
Evacuation completion time	↓
Crowd distribution imbalance	↓


The goal is not simply to detect congestion, but to demonstrate that prediction + intervention improves crowd flow.


---

🤗 Hugging Face

The hackathon requires Hugging Face to be used in the build.

The architecture is designed to support Hugging Face-hosted models for learned components such as:

Crowd-flow forecasting

Event/context understanding

Future multimodal/vision models

Model evaluation and experimentation


The final implementation should explicitly integrate a Hugging Face model into the prediction/decision pipeline rather than treating Hugging Face only as a dependency.


---

🛠 Tech Stack

Computer Vision

Python

YOLOv8 / Ultralytics

OpenCV

NumPy


Crowd Intelligence

Python

Graph-based modelling

Capacity-constrained simulation

Density-aware A*

Forecasting


Backend

FastAPI

Pydantic

Uvicorn


Visualisation

Gradio

Plotly

OpenCV


AI / ML

Hugging Face

Machine Learning

Time-series forecasting

Computer Vision


Testing

Pytest



---

📁 Repository Structure

Crowd-Management-system/
│
├── CROWD ALERT SYSTEM
├── GRID DENSITY MAPPER
├── Temple route planner
├── crowd behaviour analysis
│
├── grandprix/
│   ├── __init__.py
│   ├── api.py
│   ├── core.py
│   └── demo.py
│
├── tests/
│   └── test_grandprix.py
│
├── GRANDPRIX_ENGINE.md
├── requirements-grandprix.txt
└── README.md


---

🎯 Objectives

The system aims to:

Prevent dangerous crowd congestion

Predict bottlenecks before they become critical

Improve crowd distribution

Reduce unnecessary travel time

Assist event-control teams

Provide dynamic rerouting recommendations

Support emergency evacuation

Turn raw CCTV observations into actionable crowd-flow intelligence



---

👨‍💻 Author

Himanshu Pathak

B.Tech — Computer Science & Engineering

GitHub:

https://github.com/HimanshuPathak2725


---

📜 License

This project is currently developed as a hackathon/research prototype.

See the repository for licensing information and third-party dependency notices.


---

⭐ Project Vision

> Don't wait for the crowd to become dangerous. Predict where it will happen, simulate the consequences, and reroute people before the bottleneck forms.



🏁 From crowd detection → to crowd intelligence → to crowd-flow optimisation.