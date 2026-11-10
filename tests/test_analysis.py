import json
import tempfile
import unittest
from pathlib import Path

from heatbridge_pk.analysis import paired_bootstrap_ci, run_analysis, run_sweep, summarise
from heatbridge_pk.core import allocate, effective_capacity, evaluate, generate_scenarios
from heatbridge_pk.cli import main


class StressSettingTests(unittest.TestCase):
    def test_capacity_scale_respected(self):
        n, s = generate_scenarios(1, 20, 4, 5)
        rows = allocate(n, s, "nearest", capacity_scale=0.5)
        for shelter in s:
            served = sum(r["served"] for r in rows if r["shelter_id"] == shelter.shelter_id)
            self.assertLessEqual(served, effective_capacity(shelter, 0.5) + 1e-6)

    def test_reach_limit_respected(self):
        n, s = generate_scenarios(2, 20, 4, 6)
        for policy in ("nearest", "vulnerability_first", "resilience_aware"):
            for row in allocate(n[:20], s[:4], policy, max_distance_km=5.0):
                self.assertLessEqual(row["distance_km"], 5.0 + 1e-9)

    def test_surplus_capacity_serves_everyone_without_reach_limit(self):
        n, s = generate_scenarios(1, 10, 3, 8)
        result = evaluate(n, s, "resilience_aware", capacity_scale=1000.0)
        self.assertAlmostEqual(result["population_coverage"], 1.0, places=9)

    def test_invalid_settings_rejected(self):
        n, s = generate_scenarios(1, 2, 1, 2)
        with self.assertRaises(ValueError):
            allocate(n, s, "nearest", capacity_scale=0.0)
        with self.assertRaises(ValueError):
            allocate(n, s, "nearest", max_distance_km=-1.0)


class AnalysisTests(unittest.TestCase):
    def test_bootstrap_is_deterministic_and_brackets_mean(self):
        diffs = [0.1, 0.2, 0.15, 0.05, 0.3, 0.25]
        a = paired_bootstrap_ci(diffs, seed=1, replicates=500)
        b = paired_bootstrap_ci(diffs, seed=1, replicates=500)
        self.assertEqual(a, b)
        self.assertLessEqual(a[0], sum(diffs) / len(diffs))
        self.assertGreaterEqual(a[1], sum(diffs) / len(diffs))

    def test_summary_shape(self):
        rows = run_sweep(4, 8, 3, 11, capacity_scales=(1.0, 2.0), reach_limits=(None, 5.0))
        self.assertEqual(len(rows), 2 * 2 * 4 * 3)
        summary = summarise(rows, seed=11)
        self.assertEqual(len(summary["settings"]), 4)
        first = summary["settings"][0]
        self.assertIn("vulnerability_first", first["difference_vs_nearest"])
        self.assertNotIn("nearest", first["difference_vs_nearest"])

    def test_end_to_end_analysis_writes_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            run_analysis(out, n_scenarios=3, n_neighbourhoods=6, n_shelters=2, seed=3)
            loaded = json.loads((out / "results.json").read_text())
            self.assertTrue(loaded["synthetic_only"])
            self.assertTrue((out / "results.md").exists())
            self.assertTrue((out / "sweep_metrics.csv").exists())

    def test_cli_experiment_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            main(["experiment", "--output-dir", directory, "--scenarios", "2", "--neighbourhoods", "5",
                  "--shelters", "2", "--capacity-scale", "2", "--max-distance-km", "8"])
            loaded = json.loads((Path(directory) / "aggregate_metrics.json").read_text())
            self.assertEqual(loaded["capacity_scale"], 2.0)


if __name__ == "__main__":
    unittest.main()
