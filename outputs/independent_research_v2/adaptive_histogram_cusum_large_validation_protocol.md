# Frozen histogram CUSUM larger shifted-Z validation

## Question

Does the original frozen histogram CUSUM boundary (h=8.5945561755) keep shifted-Z stable-profile false switches below 25 per 100,000 monitored shots with useful episode-level precision? Two earlier 500-episode streams had point rates 24.44 and 23.78, but cluster-bootstrap 95% intervals crossed 25.

## Design

- Detector-score-only simulator stream; no logical outcomes are generated or read.
- Keep histogram edges, profile likelihoods, initialization (first 100 shots), event logic, and h=8.5945561755 fixed. Do not recalibrate or tune.
- Generate 5,000 independent 1,000-shot episodes for stable Z-biased profile at measurement probability .006 using fresh seed 2026111901. Monitor shots 101–1,000, for 4,500,000 monitored shots.
- Primary metric: false profile switches per 100,000 monitored shots. Compute a percentile 95% bootstrap interval by resampling whole episodes (not individual shots), with 20,000 bootstrap replicates and fixed analysis seed 2026111902, in batches to bound memory.
- Advancement for this narrow false-alarm question requires the bootstrap upper endpoint <=25/100,000. Any failure or inconclusive interval rejects a statistical-control claim at this evidence level. Transition detection and logical utility are outside scope.
- Stop after this one stream and analysis. No threshold adjustment or follow-on sampling based on the result.

## Reproduction

From the repository root run:

```bash
python outputs/independent_research_v2/adaptive_histogram_cusum_large_validation.py
```

This is development-only evidence, not a sealed or confirmatory evaluation. The seed is fresh relative to prior CUSUM studies. Expected workload is 5,000 episodes / 5,000,000 detector-score samples, with no Q-SHIFT logical-circuit samples.
