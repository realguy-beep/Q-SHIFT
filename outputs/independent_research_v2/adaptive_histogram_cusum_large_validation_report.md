# Larger fresh shifted-Z CUSUM validation failed

## Question and frozen design

This development study asked whether the original histogram CUSUM boundary (h=8.5945561755) controls stable shifted-Z false switches below 25 per 100,000 monitored shots with episode-level precision. The threshold, bins, likelihoods, initialization, and switch logic were unchanged. A fresh 5,000-episode stream (1,000 shots/episode, measurement p=.006, seed 2026111901) was scored; episodes were the bootstrap unit. No logical outcomes were generated.

## Result

The stream produced 1,141 false switches over 4,500,000 monitored shots: 25.36 per 100,000. A 20,000-replicate episode-cluster percentile bootstrap (seed 2026111902) gave a 95% interval of 23.96–26.80 per 100,000. The point rate exceeds the fixed limit and the upper endpoint does not clear it. The predeclared advancement gate failed.

This fresh larger stream changes the interpretation of the earlier two 500-episode point passes: the fixed threshold is not supported as controlling shifted-Z false alarms under the tested measurement shift. It does not establish a general hardware false-alarm rate, and it says nothing about logical utility.

## Accounting and reproduction

- Unique detector-score samples: 5,000,000; these are not Q-SHIFT logical-circuit samples. The cumulative Q-SHIFT development sample count remains 338,036,200.
- Runtime: 4.96 seconds; peak RSS: 718,668 KiB (includes imported scientific stack).
- Software: Python 3.12.14, NumPy 2.5.5, Stim 1.16.0.
- Command: `./.venv/bin/python outputs/independent_research_v2/adaptive_histogram_cusum_large_validation.py`
- Script SHA-256 and complete result are in `adaptive_histogram_cusum_large_validation_results.json`.
- Protocol: `adaptive_histogram_cusum_large_validation_protocol.md`.

No threshold tuning, additional sampling, sealed evaluation, or confirmatory evaluation was performed.
