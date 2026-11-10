"""Stress sweep, paired policy comparison and figures for HeatBridge-PK.

The sweep varies two things that the default experiment holds fixed:

* ``capacity_scale``: multiplies every shelter's usable capacity, from a severe
  shortage to a surplus;
* ``max_distance_km``: an optional reach limit, so a neighbourhood can only use
  shelters within that straight-line distance.

For every setting, each policy is scored on the same synthetic scenarios, so
policy differences are paired by scenario. Confidence intervals are percentile
bootstrap intervals over scenarios. Everything here runs on the standard
library; the chart needs matplotlib and is skipped with a message if it is
missing.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .core import POLICIES, Neighbourhood, Shelter, allocate, evaluate, generate_scenarios, write_csv

CAPACITY_SCALES: Tuple[float, ...] = (0.5, 1.0, 2.0, 4.0, 8.0)
REACH_LIMITS: Tuple[Optional[float], ...] = (None, 5.0)
METRICS: Tuple[str, ...] = (
    "population_coverage",
    "risk_weighted_coverage",
    "high_vulnerability_coverage",
    "low_vulnerability_coverage",
    "equity_gap_high_minus_low",
    "mean_travel_distance_km",
    "mean_service_resilience",
)
BOOTSTRAP_REPLICATES = 2000


def _reach_label(max_distance_km: Optional[float]) -> str:
    return "none" if max_distance_km is None else "{:g}km".format(max_distance_km)


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def paired_bootstrap_ci(differences: Sequence[float], seed: int,
                        replicates: int = BOOTSTRAP_REPLICATES) -> Tuple[float, float]:
    """Percentile 95% interval for the mean of paired per-scenario differences."""
    if not differences:
        raise ValueError("differences must be non-empty")
    rng = random.Random(seed)
    n = len(differences)
    means = sorted(_mean([differences[rng.randrange(n)] for _ in range(n)]) for _ in range(replicates))
    low = means[int(0.025 * (replicates - 1))]
    high = means[int(0.975 * (replicates - 1))]
    return low, high


def _group(items: Sequence, n_scenarios: int) -> List[List]:
    groups: List[List] = [[] for _ in range(n_scenarios)]
    for item in items:
        groups[item.scenario_id].append(item)
    return groups


def run_sweep(n_scenarios: int = 60, n_neighbourhoods: int = 35, n_shelters: int = 9, seed: int = 17,
              capacity_scales: Sequence[float] = CAPACITY_SCALES,
              reach_limits: Sequence[Optional[float]] = REACH_LIMITS) -> List[Dict[str, object]]:
    """Return one row per (setting, scenario, policy)."""
    neighbourhoods, shelters = generate_scenarios(n_scenarios, n_neighbourhoods, n_shelters, seed)
    n_groups: List[List[Neighbourhood]] = _group(neighbourhoods, n_scenarios)
    s_groups: List[List[Shelter]] = _group(shelters, n_scenarios)
    rows: List[Dict[str, object]] = []
    for scale in capacity_scales:
        for reach in reach_limits:
            for sid in range(n_scenarios):
                for policy in POLICIES:
                    assigned = allocate(n_groups[sid], s_groups[sid], policy, scale, reach)
                    metrics = evaluate(n_groups[sid], s_groups[sid], policy, scale, reach, rows=assigned)
                    rows.append({
                        "capacity_scale": scale,
                        "reach_limit": _reach_label(reach),
                        "scenario_id": sid,
                        "policy": policy,
                        **{k: round(v, 6) for k, v in metrics.items()},
                    })
    return rows


def summarise(rows: Sequence[Dict[str, object]], seed: int) -> Dict[str, object]:
    """Policy means per setting, and paired differences against ``nearest`` with 95% CIs."""
    settings = sorted({(float(r["capacity_scale"]), str(r["reach_limit"])) for r in rows},
                      key=lambda item: (item[0], item[1] != "none", item[1]))
    out: List[Dict[str, object]] = []
    for scale, reach in settings:
        subset = [r for r in rows if float(r["capacity_scale"]) == scale and r["reach_limit"] == reach]
        by_policy = {p: sorted((r for r in subset if r["policy"] == p), key=lambda r: int(r["scenario_id"]))
                     for p in POLICIES}
        means = {p: {m: round(_mean([float(r[m]) for r in by_policy[p]]), 4) for m in METRICS}
                 for p in POLICIES}
        ratio = round(_mean([float(r["capacity_to_demand_ratio"]) for r in by_policy["nearest"]]), 4)
        diffs: Dict[str, Dict[str, Dict[str, float]]] = {}
        for policy in POLICIES[1:]:
            diffs[policy] = {}
            for metric in METRICS:
                paired = [float(a[metric]) - float(b[metric])
                          for a, b in zip(by_policy[policy], by_policy["nearest"])]
                low, high = paired_bootstrap_ci(paired, seed)
                diffs[policy][metric] = {"mean": round(_mean(paired), 4),
                                         "ci95_low": round(low, 4), "ci95_high": round(high, 4)}
        out.append({"capacity_scale": scale, "reach_limit": reach,
                    "mean_capacity_to_demand_ratio": ratio, "scenarios": len(by_policy["nearest"]),
                    "policy_means": means, "difference_vs_nearest": diffs})
    return {"synthetic_only": True, "seed": seed, "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "settings": out}


def markdown_table(summary: Dict[str, object]) -> str:
    """Compact table of the two headline metrics per setting and policy."""
    lines = [
        "| Capacity scale | Reach limit | Capacity / demand | Policy | Population coverage | "
        "Risk-weighted coverage | High-vuln. coverage | Low-vuln. coverage | Service resilience | Mean distance (km) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for setting in summary["settings"]:  # type: ignore[index]
        for policy in POLICIES:
            m = setting["policy_means"][policy]
            lines.append("| {} | {} | {:.2f} | {} | {:.3f} | {:.3f} | {:.3f} | {:.3f} | {:.3f} | {:.2f} |".format(
                setting["capacity_scale"], setting["reach_limit"], setting["mean_capacity_to_demand_ratio"],
                policy, m["population_coverage"], m["risk_weighted_coverage"],
                m["high_vulnerability_coverage"], m["low_vulnerability_coverage"],
                m["mean_service_resilience"], m["mean_travel_distance_km"]))
    return "\n".join(lines) + "\n"


def plot(summary: Dict[str, object], path: Path) -> bool:
    """Two-panel chart: risk-weighted and low-vulnerability coverage by capacity. Returns False if skipped."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping the figure (pip install -r requirements.txt)")
        return False
    colours = {"nearest": "#8a94a8", "vulnerability_first": "#2b5ce6", "resilience_aware": "#0f1932"}
    styles = {"none": "-", "5km": "--"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, metric, title in zip(axes, ("risk_weighted_coverage", "low_vulnerability_coverage"),
                                 ("Risk-weighted coverage", "Coverage of low-vulnerability areas")):
        for reach in ("none", "5km"):
            settings = [s for s in summary["settings"] if s["reach_limit"] == reach]  # type: ignore[index]
            xs = [s["capacity_scale"] for s in settings]
            for policy in POLICIES:
                ys = [s["policy_means"][policy][metric] for s in settings]
                ax.plot(xs, ys, styles[reach], marker="o", color=colours[policy],
                        label="{} ({} reach limit)".format(policy, "no" if reach == "none" else "5 km"))
        ax.set_xscale("log", base=2)
        ax.set_xticks(list(CAPACITY_SCALES))
        ax.set_xticklabels(["x{:g}".format(c) for c in CAPACITY_SCALES])
        ax.set_xlabel("Shelter capacity scale")
        ax.set_title(title)
        ax.set_ylim(0, 1.02)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Mean over 60 synthetic scenarios")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return True


def run_analysis(output_dir: Path, n_scenarios: int = 60, n_neighbourhoods: int = 35, n_shelters: int = 9,
                 seed: int = 17) -> Dict[str, object]:
    rows = run_sweep(n_scenarios, n_neighbourhoods, n_shelters, seed)
    summary = summarise(rows, seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "sweep_metrics.csv", rows)
    (output_dir / "results.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output_dir / "results.md").write_text(markdown_table(summary), encoding="utf-8")
    plot(summary, output_dir / "figures" / "coverage_by_capacity.png")
    return summary
