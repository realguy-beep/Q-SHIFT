# Design-simulation RNG provenance note

The frozen design simulator creates one `numpy.random.Generator(PCG64(seed))` per Welch scenario and consumes it sequentially across the four prespecified true effects in order: −0.0002, −0.0003, −0.0004, −0.0005. The authoritative initialization seeds are the seven values in `VALIDATION_SEED_INVENTORY.json` under `analysis_rngs.welch_scenario_seeds`.

The frozen `DESIGN_SIMULATION_RESULTS.json` also has a per-row field named `seed` that adds the effect-row index to the scenario seed. Those offsets were **not** used to initialize separate generators; the field is a misleading row tag, not an actual independent stream. The results are reproducible from the scenario seed plus the source's fixed effect order, but this metadata defect is recorded rather than silently editing the frozen simulation output/source. Future versions should record `scenario_seed` and `effect_order` explicitly.

Bootstrap-t uses one separately initialized RNG per bootstrap scenario, as listed in `bootstrap_t_scenario_seeds`. The p=0 simulation uses the single seed `p0_safety_seed` and consumes cases sequentially. Benchmark calibration/evaluation streams are individually allocated and listed by root.
