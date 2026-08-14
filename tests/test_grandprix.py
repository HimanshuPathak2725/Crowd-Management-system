from grandprix.core import DigitalTwin


def test_density_weighted_router_avoids_hot_zone():
    twin = DigitalTwin()
    twin.ingest({"choke": 3.5, "north": 0, "south": 0})
    path, _ = twin.graph.shortest_path("gate_a", "exit_b", twin.density)
    assert path
    assert "choke" not in path or len(path) > 2


def test_forecast_returns_15_points():
    twin = DigitalTwin()
    twin.ingest({"choke": 1.0})
    forecast = twin.forecast(15)
    assert len(forecast["choke"]) == 15


def test_snapshot_has_risk():
    twin = DigitalTwin()
    twin.ingest({"choke": 4.0})
    zone = next(z for z in twin.snapshot()["zones"] if z["zone"] == "choke")
    assert zone["risk"] == "EMERGENCY"
