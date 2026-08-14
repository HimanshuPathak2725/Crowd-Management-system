# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Hugging Face forecaster placeholder (`grandprix/forecasting.py`)
- Root `requirements.txt` with full dependency tree
- `.gitignore` for Python/ML projects
- CORS middleware and structured logging in API
- Capacity-aware density capping in simulation

### Security
- Removed `reload=True` from production API runner
- Removed `__pycache__` from repository
- Added security-related dependencies (passlib, python-jose, slowapi)

### Fixed
- `spawn()` now returns actual created count instead of requested count
- Density updates capped at node capacity to prevent overflow

## [0.1.0] - 2026-08-14
### Added
- Initial GrandPrix digital twin engine
- FastAPI control plane
- Venue graph simulation with density-weighted A* routing
- EWMA-based bottleneck forecasting
- Dynamic rerouting against predicted congestion
- CV modules: Crowd Alert, Grid Density, Route Planner, Behaviour Analysis
