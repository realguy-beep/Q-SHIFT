# Episode-cluster intervals weaken the frozen CUSUM false-alarm claim

## Audit

Replayed the same eight 500-episode stable validation streams at the original frozen threshold h=8.5945561755. All eight false-switch totals matched the previously saved results exactly. For each condition, 20,000 episode-cluster bootstrap resamples produced a percentile 95% interval for false switches per 100k monitored shots. The replay adds zero unique stochastic samples.

## Results

The intervals remained below limits for nominal X/Z and shifted X profiles. Shifted Z did not:

- Initial validation: 110 false switches, 24.44/100k; cluster-bootstrap 95% interval 20.22–28.89, against a 25 limit.
- Fresh frozen-threshold validation: 107 false switches, 23.78/100k; interval 19.33–28.67, against a 25 limit.

Thus the original threshold passed the predeclared point-rate gates twice, but the available independent streams do not establish that the shifted-Z rate is below 25/100k with 95% episode-level precision. The earlier freshly recalibrated threshold had point rate 28.89/100k and already failed.

## Interpretation

Keep the detector-only histogram CUSUM as an unresolved simulator lead, with fast transition detection and low point false-switch counts in five of six validation strata. Do not claim statistically bounded shifted-Z false-alarm control. No additional threshold adjustment or samples were made.
