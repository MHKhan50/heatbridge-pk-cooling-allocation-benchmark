"""Command-line interface for HeatBridge-PK."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .analysis import run_analysis
from .core import POLICIES, allocate, evaluate, generate_scenarios, scenario_rows, write_csv


def _add_size_args(parser: argparse.ArgumentParser, output_default: str) -> None:
    parser.add_argument("--output-dir", default=output_default)
    parser.add_argument("--scenarios", type=int, default=60)
    parser.add_argument("--neighbourhoods", type=int, default=35)
    parser.add_argument("--shelters", type=int, default=9)
    parser.add_argument("--seed", type=int, default=17)


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="HeatBridge-PK synthetic cooling-centre allocation benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_size_args(sub.add_parser("generate", help="generate reproducible synthetic scenarios"), "data")
    exp = sub.add_parser("experiment", help="evaluate allocation policies at one setting")
    _add_size_args(exp, "outputs")
    exp.add_argument("--capacity-scale", type=float, default=1.0)
    exp.add_argument("--max-distance-km", type=float, default=None)
    _add_size_args(sub.add_parser("analyze", help="capacity and reach sweep with paired bootstrap CIs"), "outputs")
    args = parser.parse_args(argv)
    out = Path(args.output_dir)

    if args.command == "analyze":
        summary = run_analysis(out, args.scenarios, args.neighbourhoods, args.shelters, args.seed)
        print((out / "results.md").read_text(encoding="utf-8"))
        print("Settings: {}. Wrote results.json, results.md, sweep_metrics.csv and figures/ to {}".format(
            len(summary["settings"]), out))  # type: ignore[arg-type]
        return

    ns, ss = generate_scenarios(args.scenarios, args.neighbourhoods, args.shelters, args.seed)
    if args.command == "generate":
        nr, sr = scenario_rows(ns, ss)
        write_csv(out / "neighbourhoods.csv", nr)
        write_csv(out / "shelters.csv", sr)
        print("Generated {} neighbourhoods and {} shelters across {} synthetic scenarios in {}".format(
            len(ns), len(ss), args.scenarios, out))
        return

    out.mkdir(parents=True, exist_ok=True)
    summaries: List[Dict[str, object]] = []
    assignments: List[Dict[str, object]] = []
    for sid in range(args.scenarios):
        n_group = [n for n in ns if n.scenario_id == sid]
        s_group = [s for s in ss if s.scenario_id == sid]
        for policy in POLICIES:
            rows = allocate(n_group, s_group, policy, args.capacity_scale, args.max_distance_km)
            metrics = evaluate(n_group, s_group, policy, args.capacity_scale, args.max_distance_km, rows=rows)
            summaries.append({"scenario_id": sid, "policy": policy, **{k: round(v, 6) for k, v in metrics.items()}})
            assignments.extend({"policy": policy, **row} for row in rows)
    write_csv(out / "scenario_metrics.csv", summaries)
    write_csv(out / "assignments.csv", assignments)
    means: Dict[str, Dict[str, float]] = {}
    for policy in POLICIES:
        rows_p = [r for r in summaries if r["policy"] == policy]
        means[policy] = {key: round(sum(float(r[key]) for r in rows_p) / len(rows_p), 6)
                         for key in rows_p[0] if key not in ("scenario_id", "policy")}
    payload = {"seed": args.seed, "scenarios": args.scenarios, "capacity_scale": args.capacity_scale,
               "max_distance_km": args.max_distance_km, "synthetic_only": True, "policy_means": means}
    (out / "aggregate_metrics.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(means, indent=2))
    print("Wrote results to {}".format(out))


if __name__ == "__main__":
    main()
