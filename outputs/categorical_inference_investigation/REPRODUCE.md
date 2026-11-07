# Reproduction

Run commands from `outputs/categorical_inference_investigation/` using Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0 and NumPy 2.5.3.

## Verify and reproduce toy evidence

```powershell
python -B baseline_reproduction.py
python -B "C:\Users\LENOVO\Documents\Codex\2026-11-03\referenced-chatgpt-conversation-this-is-an\outputs\categorical_decoder_feasibility\test_categorical_reference.py" -v
python -B categorical_dem_analysis.py
python -B separator_ablation.py
python -B controlled_cycle_variants.py
python -B controlled_variants.py
python -B toy_ve_analysis.py
```

The old unit-test command uses the original read-only source path; `-B` prevents bytecode cache writes. The product-of-marginals variant is an exploratory confounded sensitivity analysis and is labeled as such in its saved JSON.

## Rebuild deterministic circuit fragments

```powershell
python -B run_fragment.py --rounds 1
python -B run_fragment.py --rounds 2
python -B run_fragment.py --rounds 3
python -B run_fragment.py --rounds 4
python -B run_fragment.py --rounds 5
python -B circuit_heuristics.py
```

Rounds 4–5 only extract deterministic effects and save a resource preflight; the runner skips posterior allocation above 2 GiB. Rounds 1–3 run structured exact inference. Each run writes JSON evidence into this new directory. No noisy Phase 2B sample dataset is generated.

## Final validation and integrity

```powershell
python -B -m unittest discover -v
python -B run_validation.py
python -B summarize_investigation.py
python -B build_manifest.py
python -B verify_manifest.py
```

Manifest verification checks local deliverables and the referenced old toy/Phase 2B source hashes. Re-running the commands modifies only this new investigation directory.

