"""Scenario generation and policy evaluation for HeatBridge-PK.

All generated observations are synthetic. This is a decision-policy benchmark,
not a Pakistan geospatial or epidemiological model.
"""
from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class Neighbourhood:
    scenario_id: int
    neighbourhood_id: str
    x_km: float
    y_km: float
    population_demand: int
    heat_exposure: float
    social_vulnerability: float
    mobility_barrier: float
    women_safety_barrier: float


@dataclass(frozen=True)
class Shelter:
    scenario_id: int
    shelter_id: str
    x_km: float
    y_km: float
    capacity: int
    power_reliability: float
    water_reliability: float
    accessibility: float
    women_safe_access: float


def generate_scenarios(n_scenarios: int = 60, n_neighbourhoods: int = 35,
                       n_shelters: int = 9, seed: int = 17) -> Tuple[List[Neighbourhood], List[Shelter]]:
    """Generate reproducible synthetic urban scenarios in abstract kilometre space."""
    if min(n_scenarios, n_neighbourhoods, n_shelters) < 1:
        raise ValueError("scenario and entity counts must be positive")
    rng = random.Random(seed)
    neighbourhoods: List[Neighbourhood] = []
    shelters: List[Shelter] = []
    for sid in range(n_scenarios):
        # Scenario-level shocks create correlated service degradation.
        grid_shock = rng.uniform(0.0, 0.45)
        water_shock = rng.uniform(0.0, 0.35)
        for i in range(n_neighbourhoods):
            neighbourhoods.append(Neighbourhood(
                sid, f"N{sid:04d}_{i:03d}", rng.uniform(0, 20), rng.uniform(0, 20),
                rng.randint(120, 1100), rng.uniform(0.25, 1.0),
                rng.uniform(0.15, 1.0), rng.uniform(0.0, 1.0), rng.uniform(0.0, 1.0)))
        for j in range(n_shelters):
            shelters.append(Shelter(
                sid, f"S{sid:04d}_{j:02d}", rng.uniform(0, 20), rng.uniform(0, 20),
                rng.randint(450, 2400), max(0.05, min(1.0, rng.uniform(0.55, 1.0)-grid_shock)),
                max(0.05, min(1.0, rng.uniform(0.60, 1.0)-water_shock)),
                rng.uniform(0.25, 1.0), rng.uniform(0.2, 1.0)))
    return neighbourhoods, shelters


def _distance(a, b) -> float:
    return math.hypot(a.x_km - b.x_km, a.y_km - b.y_km)


def allocate(neighbourhoods: List[Neighbourhood], shelters: List[Shelter], policy: str) -> List[dict]:
    """Allocate population demand in divisible blocks against usable shelter capacity."""
    if policy not in {"nearest", "vulnerability_first", "resilience_aware"}:
        raise ValueError(f"unknown policy: {policy}")
    remaining = {s.shelter_id: float(s.capacity) * s.power_reliability * s.water_reliability
                 for s in shelters}
    by_id = {s.shelter_id: s for s in shelters}
    if policy == "nearest":
        ordered = sorted(neighbourhoods, key=lambda n: n.neighbourhood_id)
    elif policy == "vulnerability_first":
        ordered = sorted(neighbourhoods,
                         key=lambda n: (-(n.heat_exposure*n.social_vulnerability), n.neighbourhood_id))
    else:
        ordered = sorted(neighbourhoods,
                         key=lambda n: (-(n.heat_exposure*n.social_vulnerability*(1+0.35*n.mobility_barrier)), n.neighbourhood_id))
    assignments: List[dict] = []
    for n in ordered:
        left = float(n.population_demand)
        candidates = []
        for s in shelters:
            cap = remaining[s.shelter_id]
            if cap <= 0:
                continue
            dist = _distance(n, s)
            if policy == "nearest":
                score = dist + (1-s.accessibility)*2.0
            elif policy == "vulnerability_first":
                score = dist + (1-s.accessibility)*2.5 + n.mobility_barrier*dist*0.10
            else:
                service = 0.50*s.power_reliability + 0.30*s.water_reliability + 0.20*s.women_safe_access
                barrier = n.mobility_barrier*(1-s.accessibility) + n.women_safety_barrier*(1-s.women_safe_access)
                score = dist*(1+0.45*barrier) + (1-service)*4.0
            candidates.append((score, s.shelter_id))
        for _, sid in sorted(candidates):
            if left <= 0:
                break
            served = min(left, remaining[sid])
            if served <= 0:
                continue
            s = by_id[sid]
            assignments.append({
                "scenario_id": n.scenario_id, "neighbourhood_id": n.neighbourhood_id,
                "shelter_id": sid, "demand": n.population_demand, "served": served,
                "distance_km": round(_distance(n, s), 4), "heat_exposure": n.heat_exposure,
                "social_vulnerability": n.social_vulnerability,
                "mobility_barrier": n.mobility_barrier,
                "women_safety_barrier": n.women_safety_barrier,
                "power_reliability": s.power_reliability, "water_reliability": s.water_reliability,
                "accessibility": s.accessibility, "women_safe_access": s.women_safe_access,
            })
            remaining[sid] -= served
            left -= served
    return assignments


def evaluate(neighbourhoods: List[Neighbourhood], shelters: List[Shelter], policy: str) -> Dict[str, float]:
    rows = allocate(neighbourhoods, shelters, policy)
    served_by_n: Dict[str, float] = {}
    weighted_served = 0.0
    weighted_total = 0.0
    raw_served = 0.0
    raw_total = sum(n.population_demand for n in neighbourhoods)
    distance_total = 0.0
    resilience_total = 0.0
    for n in neighbourhoods:
        weight = n.heat_exposure * n.social_vulnerability
        weighted_total += n.population_demand * weight
    for row in rows:
        served = row["served"]
        served_by_n[row["neighbourhood_id"]] = served_by_n.get(row["neighbourhood_id"], 0.0) + served
        weight = row["heat_exposure"] * row["social_vulnerability"]
        weighted_served += served * weight
        raw_served += served
        distance_total += served * row["distance_km"]
        resilience_total += served * (0.5*row["power_reliability"] + 0.3*row["water_reliability"] + 0.2*row["women_safe_access"])
    high = [n for n in neighbourhoods if n.social_vulnerability >= 0.70]
    low = [n for n in neighbourhoods if n.social_vulnerability < 0.40]
    def coverage(group):
        demand = sum(n.population_demand for n in group)
        served = sum(min(n.population_demand, served_by_n.get(n.neighbourhood_id, 0.0)) for n in group)
        return served / demand if demand else 0.0
    high_cov, low_cov = coverage(high), coverage(low)
    return {
        "population_coverage": raw_served/raw_total if raw_total else 0.0,
        "risk_weighted_coverage": weighted_served/weighted_total if weighted_total else 0.0,
        "high_vulnerability_coverage": high_cov,
        "low_vulnerability_coverage": low_cov,
        "equity_gap_high_minus_low": high_cov-low_cov,
        "mean_travel_distance_km": distance_total/raw_served if raw_served else 0.0,
        "mean_service_resilience": resilience_total/raw_served if raw_served else 0.0,
    }


def write_csv(path: Path, rows: Iterable[dict]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def scenario_rows(neighbourhoods, shelters):
    return ([n.__dict__ for n in neighbourhoods], [s.__dict__ for s in shelters])
