"""Command-line interface for HeatBridge-PK."""
import argparse
import json
from pathlib import Path
from .core import generate_scenarios, scenario_rows, write_csv, evaluate, allocate

POLICIES = ("nearest", "vulnerability_first", "resilience_aware")


def main(argv=None):
    parser = argparse.ArgumentParser(description="HeatBridge-PK synthetic cooling-centre allocation benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="generate reproducible synthetic scenarios")
    gen.add_argument("--output-dir", default="data")
    gen.add_argument("--scenarios", type=int, default=60)
    gen.add_argument("--neighbourhoods", type=int, default=35)
    gen.add_argument("--shelters", type=int, default=9)
    gen.add_argument("--seed", type=int, default=17)
    exp = sub.add_parser("experiment", help="evaluate allocation policies")
    exp.add_argument("--output-dir", default="outputs")
    exp.add_argument("--scenarios", type=int, default=60)
    exp.add_argument("--neighbourhoods", type=int, default=35)
    exp.add_argument("--shelters", type=int, default=9)
    exp.add_argument("--seed", type=int, default=17)
    args = parser.parse_args(argv)
    ns, ss = generate_scenarios(args.scenarios, args.neighbourhoods, args.shelters, args.seed)
    if args.command == "generate":
        nr, sr = scenario_rows(ns, ss)
        out = Path(args.output_dir)
        write_csv(out / "neighbourhoods.csv", nr)
        write_csv(out / "shelters.csv", sr)
        print(f"Generated {len(ns)} neighbourhoods and {len(ss)} shelters across {args.scenarios} synthetic scenarios in {out}")
        return
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summaries, assignments = [], []
    for sid in range(args.scenarios):
        n_group = [n for n in ns if n.scenario_id == sid]
        s_group = [s for s in ss if s.scenario_id == sid]
        for policy in POLICIES:
            metrics = evaluate(n_group, s_group, policy)
            summaries.append({"scenario_id": sid, "policy": policy, **{k: round(v, 6) for k, v in metrics.items()}})
            for row in allocate(n_group, s_group, policy):
                assignments.append({"policy": policy, **row})
    write_csv(out / "scenario_metrics.csv", summaries)
    write_csv(out / "assignments.csv", assignments)
    means = {}
    for policy in POLICIES:
        rows = [r for r in summaries if r["policy"] == policy]
        means[policy] = {key: round(sum(r[key] for r in rows)/len(rows), 6)
                         for key in rows[0] if key not in ("scenario_id", "policy")}
    (out / "aggregate_metrics.json").write_text(json.dumps({"seed": args.seed, "scenarios": args.scenarios, "synthetic_only": True, "policy_means": means}, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(means, indent=2))
    print(f"Wrote results to {out}")

if __name__ == "__main__":
    main()
