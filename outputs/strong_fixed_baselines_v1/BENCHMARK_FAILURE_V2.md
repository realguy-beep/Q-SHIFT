# Preserved benchmark-v2 failure record

This is a benchmark-only software failure. It did not touch the 3,660,000-shot study allocation, Stage 5 evidence, or sealed test material.

- Exact command: `python -B outputs/strong_fixed_baselines_v1/benchmark_pipeline.py`
- Failure: `TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'`
- Location: `benchmark_pipeline.py`, at the then-current allocation projection which attempted to sum `shots` for study seed entries before the seed inventory recorded shot counts.
- Work completed before failure: 3,500 benchmark-only Stim shots, with fresh seeds `18000001611`–`18000001615` (500 at each of template p=0, .01, .02; 1,000 calibration and 1,000 evaluation shots at p=.008). No run dataset or result file was committed; data remained in process memory and were released at exit.
- Study/evaluation shots generated: **0**.
- Recovery: the inventory generator now records the shot count for every sample stream and validates that included streams sum exactly to 3,660,000. The five benchmark-v2 seeds are retired. The comprehensive benchmark uses five additional, disjoint benchmark-v3 seeds.
- Experimental interpretation: none. This failure generated no decoder comparison or model-selection result.
