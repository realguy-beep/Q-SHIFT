# Experiment log and phase decisions

## Phase checkpoints

| Checkpoint | Work | Finding / action |
|---|---|---|
| Audit | Read original source, CSV schema, saved-model context, and prior report; inspected Stim circuit and DEM. | Original experiment is distance 3 / 3 rounds / 8 detectors / 1 observable and only after-Clifford depolarizing. Prior adaptive advantage remains unproven. See `PHASE1_AUDIT.md`. |
| Controlled channels and baselines | Built explicit single-qubit Pauli composition after each CX and measurement X flips before M/MR, preserving the ideal circuit skeleton. Compared fixed matching, noise-informed matching, pooled lookup, and per-regime lookup. | All six circuits retain the same detector and observable schema. PyMatching requires Stim's `approximate_disjoint_errors=True` for multi-component Pauli channels. See `experiment_config.json`. |
| Pilot selector (rate-only) | `results/composition_results_v3.json`; 10 seeds, rate-only validation selection, 4,000-shot blocks, 500-shot windows. | 29 switches; 589 errors vs fixed's 558 / 480,000; paired p=0.00102. Harmful pilot preserved. Its selector reused threshold-validation samples, so it is not the final policy estimate. |
| Safeguarded selector | New 10-seed family, seed base 20271215. First validation half tunes threshold; second independent validation half tests paired lookup-vs-matching. Lookup requires fewer errors and exact McNemar p<0.0125 (four-way Bonferroni gate). | No regime passed the gate. Detector regime estimates remained accurate, but adaptive decoding made zero switches and tied fixed matching. This is the primary result in `results/composition_results_v4_guarded.json`. |

## Preserved run artifacts

- `results/composition_results.json` and `results/composition_results_v2.json`: earlier channel-composition pilots and intermediate analysis.
- `results/composition_results_v3.json`: rate-only selector that switched and performed worse; retained as a failed approach.
- `results/composition_results_v4_guarded.json`: final guarded fresh-seed experiment.
- `results/smoke*.json`: small development runs; excluded from all research claims.
- `raw/seed_*.npz`: earlier raw checkpoints. `raw/v4_seed_*_tr30000_va10000_te20000.npz` are the ten final shot-level bundles. SHA-256 hashes are in `raw/manifest_guarded_v4.json`.
- `figures/`: final confidence-interval plots generated from the final result JSON.

No existing artifact was deleted. Earlier pilot results are explicitly labeled and are not pooled with the final guarded experiment.

## Largest weakness and ranked improvements

The largest scientific weakness is that composition is detectable from detector statistics, but the trained lookup decoders do not beat a matching baseline. The validation-only safeguard correctly refuses to switch; the central problem is decoder quality, not merely a need for a more aggressive selector.

1. **High value / moderate feasibility / moderate compute:** fit composition-conditioned PyMatching/DEM weights from calibration circuits, then select among those fixed matching models using the same causal detector windows. Test on fresh schedules and seeds. This targets the known-strong decoder and is the next recommended experiment.
2. **High value / moderate feasibility / high compute:** extend to distance 5+ and more rounds, then test whether composition inference remains calibrated and whether matching decisions become composition-sensitive.
3. **Moderate value / high feasibility / low compute:** vary the sequential likelihood window length and hysteresis on development-only schedules, then freeze settings before a new test schedule. Keep the paired significance gate so optimization cannot create unsupported switching.

The best justified immediate improvement was item 3's conservative selector gate. It was implemented with disjoint validation roles and tested on a fresh seed family. It avoided the earlier harmful switching but yielded no advantage. Further tuning of the current lookup selector is unlikely to add evidence until a genuinely stronger specialist decoder exists.

## Reproduction

From this directory run:

```powershell
python run_composition_experiment.py --seeds 10 --train 30000 --validation 10000 --test 20000 --output results\new_run.json
```

This writes a new results file and uniquely named raw seed bundles. For the pre-generated plots, run `python plot_results.py`; that script reads the frozen guarded result JSON and does not rerun experiments.
