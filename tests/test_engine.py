"""
tests/test_engine.py
----------------------
Uses stdlib `unittest` on purpose - no pytest install required at demo time.

Run with:  python3 -m unittest discover -s tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine import DigitalTwin, Venue  # noqa: E402

VENUE_PATH = ROOT / "venue" / "venue_graph.json"


class TestVenueLoading(unittest.TestCase):
    def test_loads_all_zones_and_edges(self):
        venue = Venue.from_json(VENUE_PATH)
        self.assertEqual(len(venue.zones), 12)
        self.assertGreater(venue.graph.number_of_edges(), 0)
        self.assertIn("gate_a", venue.entry_zones)
        self.assertIn("exit_2", venue.exit_zones)

    def test_los_thresholds_monotonic(self):
        venue = Venue.from_json(VENUE_PATH)
        t = venue.los_thresholds
        self.assertLess(t["comfortable"], t["congested"])
        self.assertLess(t["congested"], t["at_risk"])
        self.assertLess(t["at_risk"], t["crush_risk"])


class TestSimulationConservation(unittest.TestCase):
    """Occupancy should never go negative and should stay within venue-wide
    reasonable bounds - a broken flow model tends to fail these first."""

    def test_no_negative_occupancy_over_a_full_run(self):
        twin = DigitalTwin(str(VENUE_PATH), dt_s=10, horizon_ticks=6)
        for snap in twin.run_headless(300):
            for z in snap["zones"]:
                self.assertGreaterEqual(z["occupancy"], 0, f"{z['id']} went negative")
                self.assertGreaterEqual(z["capacity"] * 1.05, z["occupancy"],
                                         f"{z['id']} exceeded capacity - receiving-room throttle failed")

    def test_venue_fills_then_empties(self):
        """Sanity check the whole point of the scenario: crowd builds up during
        arrivals, and the venue is essentially empty again after mass egress."""
        twin = DigitalTwin(str(VENUE_PATH), dt_s=10, horizon_ticks=6)
        occupancies = [snap["total_occupancy"] for snap in twin.run_headless(300)]
        peak = max(occupancies)
        self.assertGreater(peak, 15000, "scenario never reached a meaningful crowd size")
        self.assertLess(occupancies[-1], peak * 0.05, "venue never drained after mass egress")


class TestForecastingAndRerouting(unittest.TestCase):
    def test_alerts_fire_during_mass_egress_and_reroutes_respond(self):
        twin = DigitalTwin(str(VENUE_PATH), dt_s=10, horizon_ticks=6)
        total_alerts = 0
        total_reroutes = 0
        for snap in twin.run_headless(300):
            total_alerts += len(snap["alerts"])
            total_reroutes += len(snap["reroutes"])
        self.assertGreater(total_alerts, 0, "no bottleneck was ever forecast - scenario or thresholds need tuning")
        self.assertGreater(total_reroutes, 0, "rerouting engine never fired in response to an alert")

    def test_alert_has_positive_lead_time(self):
        """The entire value proposition: alerts must fire with real lead time,
        not just describe what's already happened."""
        twin = DigitalTwin(str(VENUE_PATH), dt_s=10, horizon_ticks=6)
        found = False
        for snap in twin.run_headless(300):
            for a in snap["alerts"]:
                found = True
                self.assertGreater(a["lead_time_s"], 0)
        self.assertTrue(found, "no alerts fired to check lead time on")


if __name__ == "__main__":
    unittest.main()
