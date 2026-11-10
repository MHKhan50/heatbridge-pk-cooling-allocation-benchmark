# Methodology and evaluation protocol

## Scope

The benchmark isolates an allocation problem: distribute synthetic neighbourhood demand over a limited set of cooling shelters whose usable capacity is reduced by power and water reliability. The benchmark is designed to test policy trade-offs, not to estimate real-world heat illness or mortality.

## Scenario generation

Each scenario contains neighbourhood demand and shelter supply in a 20 km × 20 km abstract plane. Scenario-level power and water shocks induce correlated degradation among shelters. Neighbourhoods receive independent synthetic exposure, vulnerability, mobility-barrier, and women-safe-access-barrier values. Shelters receive capacity, power/water reliability, accessibility, and safe-access values.

## Allocation

Policies order neighbourhoods according to a fixed priority rule, then allocate each neighbourhood's demand across shelters in ascending score order. Effective shelter capacity is nominal capacity multiplied by power and water reliability. Demand can be split across shelters. Unserved demand remains uncovered.

## Stress sweep (`analyze`)

The sweep multiplies every shelter's usable capacity by 0.5, 1, 2, 4 and 8, and runs each with no reach limit and with a 5 km straight-line reach limit. All three policies are scored on the same 60 scenarios at each setting. Differences against `nearest` are computed per scenario and summarised with a percentile bootstrap over scenarios (2,000 resamples, seed 17).

## Primary outcomes

Primary outcome: risk-weighted coverage. Secondary outcomes: population coverage, high-vulnerability coverage, low-vulnerability coverage, equity gap, mean travel distance, and mean service resilience.

## Protocol for any further study

1. Freeze code and protocol before running confirmatory experiments.
2. Use at least 30 independent seeds; retain scenario-level paired comparisons.
3. Report mean, standard deviation, median, and 95% bootstrap confidence intervals for each metric and paired policy difference.
4. Correct for multiple comparisons when testing multiple policies/outcomes.
5. Run ablations removing each resilience/accessibility term.
6. Include adverse scenarios: severe grid shock, water disruption, shelter loss, concentrated vulnerability, and severe capacity shortage.
7. Publish all seeds, raw outputs, code version, and exact commands.
8. Validate assumptions with Pakistan-based heat-health, municipal, disability, gender, and emergency-management stakeholders before any operational interpretation.

## Falsifiable hypotheses (to test, not assume)

- H1: vulnerability-first allocation increases risk-weighted coverage relative to nearest-first under tight capacity.
- H2: resilience-aware allocation increases mean service resilience relative to nearest-first.
- H3: improvements in risk-weighted coverage or service resilience may incur travel-distance or overall-coverage trade-offs.

No hypothesis is asserted as supported by the synthetic results until experiments are run and uncertainty is reported.
