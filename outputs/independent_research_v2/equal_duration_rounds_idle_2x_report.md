# Twofold idle-noise robustness challenge

## Result

Only the idle arm changed: per-cycle biased data-idle Pauli probability increased from .003 to .006. Five-active-round source circuits remained at gate and measurement p=.003. At X alignment, three rounds plus idle had 694/500,000 failures versus 683/500,000 for five active rounds, RR 1.016 (95% interval .914–1.129). At Z alignment, it had 580 versus 770 failures, RR .753 (.676–.839). The equal-weight mean cell RR was .885.

The aggregate remains below .90, and neither cell is worse by more than 5% at its point estimate. However, the fixed robustness rule also required both cell point estimates below 1; X alignment failed that condition. Therefore the robustness gate fails. The X result is statistically uncertain and near-neutral, not evidence of a clear harm. The Z-aligned advantage remains statistically supported under this twofold idle stress.

## Interpretation

The initial equal-duration improvement is not uniform across the two aligned workloads as idle noise increases. Evidence now supports a narrower hypothesis: fewer active syndrome rounds may be useful for Z-aligned memory under the tested X/Z-bias family and assumed idle Pauli model. This is still a synthetic d3 result, not a hardware schedule recommendation. No further idle-rate sweep is warranted without a measured idle-noise range or a concrete deployment profile.

Artifacts: `equal_duration_rounds_idle_2x_protocol.md`, `equal_duration_rounds_idle_2x.py`, and `equal_duration_rounds_idle_2x_results.json`.
