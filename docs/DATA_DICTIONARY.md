# Data dictionary

All generated records are synthetic. Coordinates are abstract kilometres; reliability and exposure values are unit-interval scenario parameters, not measured Pakistan statistics.

## `neighbourhoods.csv`

| Field | Type | Definition | Unit / range |
|---|---|---|---|
| `scenario_id` | integer | Independent synthetic scenario identifier | integer ≥ 0 |
| `neighbourhood_id` | string | Unique neighbourhood key within generated release | identifier |
| `x_km`, `y_km` | float | Abstract planar location | km, 0–20 |
| `population_demand` | integer | Synthetic cooling-service demand | persons, 120–1100 |
| `heat_exposure` | float | Relative heat-exposure intensity | 0.25–1.0 |
| `social_vulnerability` | float | Relative social vulnerability | 0.15–1.0 |
| `mobility_barrier` | float | Relative mobility/access barrier | 0–1 |
| `women_safety_barrier` | float | Relative safe-access barrier | 0–1 |

## `shelters.csv`

| Field | Type | Definition | Unit / range |
|---|---|---|---|
| `scenario_id` | integer | Scenario identifier | integer ≥ 0 |
| `shelter_id` | string | Unique synthetic shelter key | identifier |
| `x_km`, `y_km` | float | Abstract planar location | km, 0–20 |
| `capacity` | integer | Nominal synthetic service capacity | persons, 450–2400 |
| `power_reliability` | float | Probability-like scenario service factor | 0.05–1.0 |
| `water_reliability` | float | Probability-like scenario service factor | 0.05–1.0 |
| `accessibility` | float | Relative accessibility score | 0.25–1.0 |
| `women_safe_access` | float | Relative safe-access score | 0.2–1.0 |

## Experiment outputs

`scenario_metrics.csv` contains one row per scenario-policy pair. `assignments.csv` contains positive allocations by neighbourhood and shelter. `aggregate_metrics.json` contains arithmetic means across scenarios and records the seed and synthetic-only flag.
