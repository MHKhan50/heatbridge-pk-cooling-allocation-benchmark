import unittest
from heatbridge_pk.core import generate_scenarios, allocate, evaluate

class HeatBridgeTests(unittest.TestCase):
    def test_reproducible_generation(self):
        a = generate_scenarios(2, 5, 3, 41)
        b = generate_scenarios(2, 5, 3, 41)
        self.assertEqual(a, b)

    def test_entity_counts(self):
        n, s = generate_scenarios(4, 7, 2, 3)
        self.assertEqual(len(n), 28)
        self.assertEqual(len(s), 8)

    def test_allocation_respects_capacity(self):
        n, s = generate_scenarios(1, 12, 4, 7)
        rows = allocate(n, s, "resilience_aware")
        for shelter in s:
            served = sum(r["served"] for r in rows if r["shelter_id"] == shelter.shelter_id)
            effective_capacity = shelter.capacity*shelter.power_reliability*shelter.water_reliability
            self.assertLessEqual(served, effective_capacity + 1e-6)

    def test_metrics_are_bounded(self):
        n, s = generate_scenarios(1, 12, 4, 9)
        result = evaluate(n, s, "vulnerability_first")
        for key in ("population_coverage", "risk_weighted_coverage", "high_vulnerability_coverage", "low_vulnerability_coverage", "mean_service_resilience"):
            self.assertGreaterEqual(result[key], 0.0)
            self.assertLessEqual(result[key], 1.0)

    def test_unknown_policy_rejected(self):
        n, s = generate_scenarios(1, 2, 1, 2)
        with self.assertRaises(ValueError):
            allocate(n, s, "magic")

if __name__ == "__main__":
    unittest.main()
