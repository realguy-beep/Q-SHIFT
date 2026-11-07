# Q-SHIFT Phase 2B Protocol

## Objective and status

This is a new exploratory simulation study of whether changing Pauli composition, while holding the total gate-fault probability constant, makes the existing type of PyMatching model bank specialize. It is not a controller experiment and is not hardware calibration. Phase 1, Phase 2A, and all prior outputs remain unchanged. No Phase 2A test data are used for selection or evaluation.

## Circuit and noise design

Use Stim's rotated distance-3 surface-code memory circuit with five rounds in both Z-memory and X-memory bases. This repeats the same code size and schedule across bases so a result cannot be attributed only to one logical basis. The built-in circuit's detector and observable definitions are retained. Noise changes only by replacing the generated post-Clifford `DEPOLARIZE1(0.003)` and `DEPOLARIZE2(0.003)` instructions; measurement flips stay at 0.003. The total non-identity probability at each one- or two-qubit gate-noise instruction is therefore 0.003 in all three regimes.

The three regimes are X-biased, balanced, and Z-biased. The one-qubit Pauli channel assigns 80%, 10%, and 10% of its 0.003 fault mass to dominant, Y, and minor-axis Pauli respectively; balanced assigns one third to each. For a two-qubit instruction, the fifteen non-II Pauli-pair probabilities sum to 0.003 and are proportional to the product of per-symbol weights (`I=1`, dominant Pauli `=10`, each other Pauli `=1`). This makes the pair channel explicitly specified and includes pair-correlated Pauli outcomes such as XX, XY, and YZ. Measurement-flip probability is 0.003 for all bases and regimes. These are controlled sensitivity settings, not estimates from a real device.

This is circuit-level stochastic Pauli noise applied after the same one- and two-qubit Clifford locations as the generated Stim circuit. Two-qubit Pauli-pair events are included. There are no coherent over-rotations, leakage, crosstalk between separate gates, or long-range correlated bursts. The bias ratio is an experimental design choice (10:1:1), not a claim that a particular processor has that bias.

## Data partitions and selection

For each of six cells (two memory bases by three generating regimes), collect 5,000 development/validation shots, 20,000 independent calibration shots, and 20 independent held-out roots with 10,000 paired shots each. The held-out total is 1,200,000 shots. Save detectors, logical observable labels, and the three bank predictions for every root. All three candidate decoders process identical detector samples in each root.

The bank contains the three assumed compositions in frozen order: X-biased (index 0), balanced (index 1), and Z-biased (index 2). For each memory basis, the global fixed model minimizes the equal-regime calibration error rate. The regime-informed diagnostic selects a model separately in each basis-regime calibration cell. Exact ties choose the lowest index. Validation data are used only for predeclared circuit/noise sanity checks and descriptive results; they do not select models. Test labels are withheld from selection and used only for scoring and explicitly retrospective oracle diagnostics.

Comparator A is the calibration-selected global model for the known memory basis. Comparator B is the calibration-selected regime-specific model, with the generating regime supplied only for this diagnostic. Comparator C is the balanced model, index 1. Retrospective evaluation-label per-regime and per-shot oracles are unattainable lower-bound diagnostics.

## Primary endpoint and inference

The primary estimate is the equal-weight mean over the six basis-regime cells of B LER minus A LER. Negative values favor regime-specific selection. Its confidence interval uses 100,000 percentile bootstrap draws, resampling the 20 independent roots separately within each cell. Its two-sided paired root-cluster sign-flip test uses 100,000 Monte Carlo assignments and an add-one p-value. RNG seeds are fixed in `config.json`.

Secondary root-cluster sign-flip comparisons are prespecified for each memory basis (Holm family of 2), each of the six cells (family of 6), and the twelve alternatives to A across cells (family of 12). Exact shot-level McNemar tests and Wilson intervals are descriptive; shots are not treated as independent experimental replicates for the primary inference. All decoder disagreements use paired shot arrays.

## Seeds, freeze, and stopping rules

Development/validation, calibration, held-out, diagnostic, bootstrap, and sign-flip streams use the distinct formulas in `config.json`. Before sampling, the runner scans available historical text artifacts and saved NPZ seed fields. `PRETEST_FREEZE.json` is written only after circuits, DEMs, calibration selection, seeds, source, and analysis plan pass validation and before any held-out test shot is sampled. Its hashes and actual ordering checks are reported in `CIRCUIT_VALIDATION.md` and the final manifest.

Stop without held-out sampling if any of the following fails: seed uniqueness/disjointness over recoverable records; expected detector/observable counts; zero-noise detector behavior; nonzero noise sensitivity; channel probability sums and locations; graph/DEM construction; paired decoder output shapes; calibration/test stream separation; or the frozen selection implementation. After held-out sampling starts, do not alter the protocol, candidate channels, bank, seeds, estimand, or statistical procedure. Any post-test method changes are exploratory and require a new held-out study.

## Interpretation boundary

Regime-informed decoding uses the known simulated noise condition and is not an adaptive controller. A positive result would establish only an opportunity in this specific circuit-level noise family under the documented Stim DEM approximation. It would not establish a deployable estimator, real hardware benefit, or within-circuit adaptation.
