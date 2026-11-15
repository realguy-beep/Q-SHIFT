# Preserved benchmark-v3 failure record

This was a separate runtime/resource benchmark only. It did not generate any of the study's 3,660,000 allocated samples and did not touch Stage 5 or sealed data.

- Exact command: `python -B outputs/strong_fixed_baselines_v1/benchmark_pipeline.py`
- Error: `ZeroDivisionError: float division by zero`
- Location: `benchmark_pipeline.py`, where the template throughput projection summed `benchmark_v2_template` entries even though the selected fresh stream role was `benchmark_v3_template`.
- Work completed before failure: all five fresh benchmark-v3 streams were sampled (3,500 shots total), the profile and pooled estimates and decoder arms ran, and disposable representative I/O plus synthetic bootstrap timing ran. The failure occurred while calculating the full-allocation projection. No benchmark report was emitted and temporary raw arrays were removed with the temporary directory/process.
- Consumed and retired seeds: `18000001616`–`18000001620`.
- Stage 1 study shots generated: **0**. Stage 5 shots generated: **0**.
- Repair: validate exact benchmark roles, their counts, and the 3,660,000 included-shot total before sampling; compute the projection from the active v4 role name. The next attempt uses five fresh benchmark-v4 seeds.
- Interpretation: none; the failed process did not persist results and its estimates are not research findings.
