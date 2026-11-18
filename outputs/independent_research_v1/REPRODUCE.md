# Reproduce the isolated research checkpoint

## Environment

Use Python 3.12.14. In `/workspace/qshift-independent-research-v1`, create the worktree-local environment and install the pinned research packages:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --no-input -r outputs/independent_research_v1/requirements-research.txt
```

Observed versions at checkpoint: NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, PyMatching 2.4.0, LDPC 2.4.1, NetworkX 3.7. Python package builds were installed from PyPI with TLS verification enabled. PyTorch was not installed because the screened prototype does not use it and the environment has no visible GPU. `MPLCONFIGDIR=/tmp/qshift-mpl` avoids matplotlib attempting to create a cache beneath the read-only home path.

## Checks and calculations

From the worktree root:

```bash
python3.12 outputs/independent_research_v1/zero_failure_bounds.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python -m unittest discover -s outputs/independent_research_v1 -p 'test_categorical_bp.py' -v
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/dem_preflight.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/dem_threshold_scan.py
```

The toy tests load analytically defined categorical circuits and exact-posterior code from the tracked `outputs/categorical_decoder_feasibility/` directory. The DEM preflight imports the read-only tracked Phase 2B builder. It generates circuits in memory and does not sample shots or write under historical output paths.

## Experiment provenance

- Branch: `codex/qshift-independent-research-v1`.
- Main base: `7cbc2e791a854e40ed4e840393fc8b4368d95ac2`.
- Phase 2B circuit builder SHA-256: `256826516353c5d3effb6a0b85969934ac2b61edc2848148d935087e54dffcbd`.
- Phase 2B decoder bank SHA-256: `ea88bbd9c60b027b7525d330db39df5c48fc3495a6644a9b991fa70ac2161080`.
- `research_direction_selection/PILOT_PROTOCOL.md` SHA-256: `96a08320b8f01a42f6be7b6526c8092e12e9202d0a0b2bf9738c24b8579c797a`.
- `research_direction_selection/SELECTED_DIRECTION.md` SHA-256: `6655a6f0aa28380f7145b4531eaa49af634c9e97d30815fd89a0c3cbb3e1b98f`.
- No confirmatory data or independent-test material was accessed. Development-only source-circuit shots and separate ideal-syndrome qecsim code-capacity shots are recorded in `RESULTS.json` with their scopes.

## Continuation

Continue in this same worktree and branch. Read `WORK_LOG.md`, `RESEARCH_LOG.md`, and `CLAUDE_HANDOFF.md` first. Do not repeat the existing correlation pilot. The next potentially useful step is an exactness-controlled redesign of native categorical inference on small cyclic factor graphs; the current Bethe prototype is a negative screen and must not be used on the distance-3 circuit without a revised exact-toy validation gate.

- Reproduce the bounded MPS validity/runtime preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/tensor_mps_screen.py --preflight`. This does not launch the full screen.

- Reproduce BP+LSD setup/runtime validity preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bplsd_feasibility.py --preflight`. Reproduce the fixed development run with the same command without `--preflight`; it writes to this research directory only.

- Reproduce the rare-event estimator preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/rare_event_is.py --preflight`; reproduce the main and 8-replicate development runs with the same script and respectively no flag or `--replicates 8 --shots 5000`. These runs sample approximate DEMs only.

- Reproduce exact-channel instrumentation validity/timing with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_importance_sampler.py --preflight`; reproduce the fixed main sample without `--preflight`; reproduce the two independent stability blocks using `--replicates 8 --shots 5000` and `--replicates 8 --replicate-start 8 --shots 5000`. Validate against raw Stim circuit sampling with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_sampler_crosscheck.py`.

- Reproduce the cross-entropy training/validation run with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_cross_entropy.py`; it writes its learned proposal and independent validation metrics to `categorical_cross_entropy_results.json`.

- Reproduce the memory-basis analysis from the saved independent direct-arm aggregates with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/basis_orientation_analysis.py`. It samples no new shots.

- Reproduce the distance-5 timing/shape preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/code_distance_scaling.py --preflight`; the fixed development screen runs without `--preflight`.

- Reproduce the bias-strength preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bias_crossover.py --preflight`; rerun the fixed development screen without `--preflight`.

- Reproduce the distance-7 known-profile extension preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/basis_alignment_distance7.py --preflight`; the fixed 500,000-shot-per-cell run uses the same command without `--preflight`.

- Reproduce the fixed-bond qecsim MPS 100-shot preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/tensor_mps_truncated.py --preflight`; reproduce the fixed χ=16 development screen without `--preflight`.

- Reproduce detector-only binary identification with `bias_identification.py --preflight` and then without the flag; reproduce the three-class strength stress test with `bias_strength_identification.py --preflight` and then without the flag. `bias_binary_cross_strength.py` re-scores those exact seeded streams using the earlier frozen two-class model; it does not fit a model or add independent sample streams.

- Reproduce the cross-sample LER projection with `python outputs/independent_research_v1/basis_decision_projection.py` only if needed; the saved projection is `bias_decision_projection.json`.

- Reproduce direct, independent calibration-to-memory policy validation with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/adaptive_basis_end_to_end.py --preflight`, then run without the flag. `adaptive_basis_end_to_end_first_pass_reversed.json` is an invalid implementation pass retained for audit; use only `adaptive_basis_end_to_end_results.json`.

- Reproduce the total-rate drift preflight and development run with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/adaptive_basis_rate_shift.py --preflight`, then run without the flag. It keeps the frozen classifier and compares p=.003 calibration with p=.006 logical circuits; DEM approximation threshold .004 is fixed in the protocol.

- Reproduce the exploratory calibration-prefix rescore with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/adaptive_basis_cost_frontier.py`. It uses the fixed seeds and saved logical windows; it generates no new unique sample streams.

- Reproduce the same-observable decoder-bank preflight and development run with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/same_observable_decoder_selection.py --preflight`, then run without the flag.

- Reproduce the checkerboard XZZX code/circuit preflight and 500,000-shot-per-cell screen with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_codesign.py --preflight`, then run without the flag.

- Recompute the plug-in calibration-throughput horizon with `python outputs/independent_research_v1/calibration_amortization.py`; this reads saved LER estimates and generates no shots.

- Recompute the exploratory alternating-profile resource replay with `.venv/bin/python outputs/independent_research_v1/temporal_basis_replay.py`. It reads the saved classifier-confusion and logical-window summaries and generates no new circuit samples.

- Reproduce the exact categorical toy/grid variable-elimination analysis with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_elimination.py`. It checks exhaustive posteriors, forced Stim outcomes, and sparse-grid state growth; it generates no stochastic Q-SHIFT shots.

- Reproduce the deterministic three-location Phase 2B fragment mapping with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_phase2b_fragment.py`. It uses raw measurements from forced Pauli circuits, checks XOR composition and exhaustive categorical masses, and generates no stochastic samples.

- Reproduce the six-location layer width preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_phase2b_six_location_preflight.py`, then the all-syndrome exact XOR-convolution/VE comparison with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_phase2b_six_location.py`. The second run takes about 95 seconds here; neither generates stochastic circuit shots.

- Reproduce the two-layer scope-only ordering audit with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_phase2b_two_layer_preflight.py`. It allocates no inference tables; all eight tested orders exceeded the one-million-entry cap.

- Reproduce the distance-3 round-count frontier preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/round_count_frontier.py --preflight`, then the 200,000-shot-per-cell screen with the same command without `--preflight`.

- Reproduce the bias-strength robustness preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bias_strength_robustness.py --preflight`, then the 100,000-shot-per-cell paired screen with the same command without `--preflight`.

- Reproduce the fresh frozen ratio10-vs-ratio5 validation preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bias_strength_frozen_validation.py --preflight`, then the 100,000-shot-per-cell validation with the same command without `--preflight`.

- Reproduce the d5 ratio10-vs-ratio5 preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bias_strength_distance5_validation.py --preflight`, then the 100,000-shot-per-cell run with the same command without `--preflight`.

- Reproduce the deterministic ratio5/ratio10 matching graph audit with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bias_graph_mechanism.py`. It generates no stochastic samples.

- Reproduce the archived-seed paired decision decomposition with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bias_strength_decision_replay.py`. The script verifies all stored counts and creates no new independent samples.

- Reproduce the two-qubit shared-failure fault-composition preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/shared_failure_fault_mechanism.py --preflight`, then the 100,000-shot-per-cell screen with the same command without `--preflight`.

- Reproduce the exact two-layer sparse categorical inference with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_two_layer_sparse.py`.
- Reproduce the three-layer sparse preflight and exact DP/Walsh comparison with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_three_layer_preflight.py` followed by `categorical_three_layer_sparse.py`.

- Reproduce the four-layer sparse preflight and exact DP/Walsh result with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_four_layer_preflight.py` followed by `categorical_four_layer_sparse.py`.

- Reproduce the fifth-layer scope/resource preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_five_layer_preflight.py`. It stops before mass expansion at the fixed 100M operation cap.

- Reproduce the five-layer vectorized exact pass with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_five_layer_vectorized.py`; it consumes the saved five-layer forced-signature preflight artifact and produces no stochastic samples.

- Reproduce the exact six-layer coalesced DP/Walsh result with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_six_layer_coalesced.py`. It consumes the saved six-layer forced-signature map and generates no stochastic samples.

- Reproduce the seven-layer state/support preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_seven_layer_preflight.py`. It stops before posterior expansion at the fixed 1M-state cap.


### Seven-layer parity-state exact fragment

From the repository root run:

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_seven_layer_parity.py
```

The fixed caps and validation gates are in `outputs/independent_research_v1/categorical_seven_layer_parity_protocol.md`. The script uses stored forced-outcome signatures and does not generate stochastic samples.


### Pair-cluster categorical importance sampling

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_cluster_importance.py
```

This reruns the preregistered 100-shot instrumentation/resource preflight and, if the 300-second projection passes, the fixed six-condition development screen. The exact seeds, grouping, estimator, and stop rules are in `categorical_cluster_importance_protocol.md`.


### Native-XCX XZZX screen

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_native_xcx.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_native_xcx.py
```

The first command performs exact conjugation/resource checks and the 100-shot/cell timing gate; the second is the fixed 500k-shot/cell development run. Hardware/noise assumptions and interpretation limits are in `xzzx_native_xcx_protocol.md`.


### Complementary native-XCX orientation

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_native_orientation.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_native_orientation.py
```

The run is limited to CSS, original, and complementary patterns at d3/d5 under Z-biased noise. See `xzzx_native_orientation_protocol.md`.


### Spatial hotspot local-versus-pooled matching

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/spatial_noise_decoder.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/spatial_noise_decoder.py
```

See the fixed noise map and shared DEM threshold amendment in `spatial_noise_decoder_protocol.md`.


### Distance-9 basis-alignment extension

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/basis_alignment_d9.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/basis_alignment_d9.py
```

The fixed d9 protocol and ratio interval definition are in `basis_alignment_d9_protocol.md`.


### Biased planar MPS code-capacity screen

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/tensor_mps_biased.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/tensor_mps_biased.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/tensor_mps_biased_replication.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/tensor_mps_biased_replication.py
```

These are code-capacity experiments only; see their fixed protocols.


### Biased MPS averaged-mode ablation

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/tensor_mps_biased_mode.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/tensor_mps_biased_mode.py
```


### Exact seven-layer tensor-train rank audit

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_seven_layer_tt.py
```

See `categorical_seven_layer_tt_protocol.md` for rank tolerances and stop gate.


### All-location fault composition

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/all_fault_mechanism.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/all_fault_mechanism.py
```

Seeds, conditions, gates, and limitations are fixed in `all_fault_mechanism_protocol.md`.


### Existing-data basis-alignment scaling synthesis

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/basis_scaling_synthesis.py
```

This recomputes a descriptive summary from fixed embedded counts; it generates no samples.


### Native XZZX versus aligned-CSS existing-data audit

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/basis_matched_xzzx_comparison.py
```

No samples are generated; inputs are fixed summaries in `RESULTS.json`.


### d5 CSS/XZZX memory-basis factorial

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_basis_factorial.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_basis_factorial.py
```

Protocol, seeds, gates, and resource assumptions: `xzzx_basis_factorial_protocol.md`.


### Pinned source audit

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/implementation_source_audit.py
```

The script fetches only public, version-pinned GitHub raw source/docs and records hashes; it also compares installed qecsim MPS source to its tag. Paper-record APIs remain proxy-blocked.


The factorial result also includes a post-hoc equal-weight mix summary; this is computed from the same fixed samples and adds no shots. Treat the mix as workload-specific descriptive analysis.


### Independent d5 XZZX/CSS factorial replication

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_basis_factorial.py --replication --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_basis_factorial.py --replication
```

Fixed fresh seeds and endpoint definitions are in `xzzx_basis_factorial_replication_protocol.md`.


### Fresh d3/d7 XZZX/CSS basis-factorial extension

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_basis_factorial_scale.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_basis_factorial_scale.py
```

The first failed preflight reporting attempt is retained separately; the successful identical-seed rerun generated the same unique preflight streams.


### d9 XZZX/CSS basis-workload challenge

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_basis_factorial_d9.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_basis_factorial_d9.py
```

See `xzzx_basis_factorial_d9_protocol.md` for fixed conditions and seeds.


### d11 XZZX/CSS basis-workload challenge

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_basis_factorial_d11.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_basis_factorial_d11.py
```

The preflight projected 217.6s; actual main runtime was 281.9s. Do not assume larger distances fit the same cap.


### d11 relative-target sample budget

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_d11_target_budget.py
```

This is deterministic and generates no circuit samples.


### d13 runtime feasibility only

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_basis_factorial_d13.py --preflight
```

The protocol's 300s stop gate failed; do not run the main command without a new predeclared design.


### d7 XZZX/CSS robustness at 2:1 bias

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_bias_ratio2.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_bias_ratio2.py
```


### d7 XZZX/CSS robustness at 5:1 bias

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_bias_ratio5.py --preflight
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_bias_ratio5.py
```

### d13 bit-packed throughput preflight

`MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/xzzx_d13_bitpacked.py --preflight`

The saved preflight stops before the main run because projected runtime is above the protocol cap.

### Fusion Blossom d3 graph interface screen

Install Fusion Blossom 0.2.13 in the isolated `.venv`, then run:

`MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/fusion_blossom_d3_screen.py`

The script runs a fixed 1,000-sample development screen and writes `fusion_blossom_d3_screen_results.json`.

### Min-fill exact tensor ordering challenge

`MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_seven_layer_minfill.py`

This deterministic analysis uses the saved seven-layer event map and adds no stochastic samples.

### Sequential profile calibration and reuse

- Primary detector-only validation: `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/adaptive_basis_sprt.py --preflight` then run without `--preflight`.
- Independent frozen-parameter replication: run `adaptive_basis_sprt_replication.py --preflight`, then without the flag.
- Direct fresh logical policy comparison: run `adaptive_basis_sprt_end_to_end.py --preflight`, then without the flag.
- Deterministic saved-stream reuse replay: `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/adaptive_basis_sprt_reuse.py`.
- Deterministic stable-profile expected-utility bootstrap: `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/adaptive_basis_sprt_utility_projection.py`.

The reuse and utility scripts add no unique stochastic samples. Their stable-profile assumption and projected status are stated in their protocol files.
