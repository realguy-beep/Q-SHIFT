# Experiment and evidence results

## New deterministic feasibility check

**Question:** Can Stim build a non-approximated detector error model for the Q-SHIFT categorical circuit so that the planned matched-DEM-family mechanism experiment is executable with PyMatching?

**Method:** In the isolated Python 3.12 environment, loaded the tracked Q-SHIFT Phase 2B circuit builder read-only and generated all six distance-3, five-round circuits (two memory bases by three Pauli-composition regimes). Called `circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=False)` for each circuit. No shots were generated and no outputs were written to the original Phase 2B directory.

**Result:** 0/6 conversions succeeded. All failed immediately with Stim `ValueError`: `PAULI_CHANNEL_2` requires `approximate_disjoint_errors=True` for error analysis. Runtime was under 0.01 seconds total. This deterministically confirms the pretest blocker described in the existing `outputs/correlation_mechanism_audit/FOLLOWUP_PROTOCOL.md`.

**Interpretation:** The proposed exact-vs-approximate DEM family cannot be implemented through this Stim circuit-to-DEM route for these categorical two-qubit channels. This does not establish that the approximation caused or did not cause the earlier correlation-mode interaction. It means the follow-up's primary contrast cannot be executed as written. A substitute must model categorical gate outcomes natively and be validated against the exact small-instance reference before sampling.

## Previously completed development evidence reviewed

The repository's separate `outputs/correlation_pilot/` is already a complete, independently rescored 720,000-shot development pilot. Its pooled fixed correlated arm had 3,349 errors and the uncorrelated arm had 3,532, with equal-stratum paired difference -0.00025417 and root-bootstrap 95% interval [-0.00035000, -0.00016250]. Its predeclared practical gate failed because the upper interval endpoint did not meet -0.0002. It is prior work, not an experiment run by this expedition. Its paired-error pattern is condition dependent and does not validate adaptive mode selection.

No confirmatory data were accessed. No experiment in this package establishes performance on an untouched test set or hardware.

## Categorical sum-product prototype on exact toys

**Hypothesis:** A loopy sum-product approximation over native categorical fault-location variables could preserve mutually exclusive Pauli outcomes while estimating logical-class probabilities, avoiding DEM splitting at the local channel level.

**Prototype:** `categorical_bp.py` keeps the outcome alphabet at each toy fault location and imposes detector and hypothesized logical parity checks. It compares Bethe partition estimates for logical 0 and 1. Tests use the existing independently validated one-qubit and two-qubit categorical toy models, then score BP decisions against their exhaustive exact posterior. No stochastic samples are used.

**Outcome:** The implementation returned normalized probabilities and converged on every toy syndrome, but its decoding quality is unacceptable on the one-qubit toy. It agrees with exact MAP on 2/4 syndromes and has exact-under-toy LER 0.057354 versus exact MAP 0.002646. On the two-qubit toy it agrees on 4/4 syndromes and has LER 0.060000, equal to exact MAP for that fixture. The same code therefore has a sharp topology-dependent result, not general validation.

The tests confirm interface, bounds, and full syndrome coverage. They do not certify algorithmic correctness or quality. The global observable-parity check creates additional loops. The hypothesis is rejected in this form. The result reinforces the need to validate posterior mass and logical decisions against exhaustive categorical references per topology before considering any circuit-scale approximation. No Q-SHIFT distance-3 experiment was run.

## Documented approximation-threshold sensitivity preflight

Stim's v1.16.0 documentation permits a probability threshold for approximating disjoint errors. To see whether this offers a distinct valid model family at Phase 2B's configured probabilities, generated each of the six circuits in memory and tried thresholds 0.001, 0.0018, 0.003, and 1.0 with graph decomposition enabled. For successful conversions, hashed the DEM and PyMatching weighted graph. This generated no shots and wrote only `approximation_threshold_scan.json`.

At 0.001, conversion failed in all three biased regimes because a `PAULI_CHANNEL_2` argument was 0.00178571, above the permitted maximum threshold. The balanced regimes converted. At 0.0018, 0.003, and 1.0, every condition converted, and within each condition all three successful thresholds produced exactly the same DEM and graph hashes (142 edges). Thus no alternate successful model family was found over this predeclared threshold set. This is a deterministic semantic sensitivity preflight, not a performance comparison.

## qecsim planar MPS runtime and validity preflight

Installed qecsim 1.0b9 in the isolated research environment. On identical IID depolarizing code-capacity errors at p=0.05, qecsim's untruncated planar MPS (`chi=None`, column contraction) and planar MWPM both returned recoveries in the codespace on 100 shots at d=3 and d=5. The small preflight counts were 4/3 errors at d=3 and 3/0 at d=5 (MWPM/MPS); these are not performance evidence and were not used to adjust the declared noise or seed plan.

The MPS decode time averaged 0.864 ms at d=3 and 60.9 ms at d=5. Scaling the measured decode times to the declared 5,000 shots per distance projects roughly 309 seconds of MPS decode work, already over the five-minute total cap before MWPM, generation, and bookkeeping. Per the protocol, the 5,000-shot screen was stopped before launch. Peak RSS was 147,200 KiB. qecsim emitted `Failed to load clib: libpypm.so.` and used its Python path; this warning does not invalidate return codes, but the comparison's runtime is implementation-specific. The result is a runtime feasibility gate for this exact, untruncated setup only. No Q-SHIFT circuit-level or measurement-noise samples were generated.

## BP+LSD development screen on Phase 2B circuits

LDPC 2.4.1's `BpLsdDecoder` accepted the flattened approximate DEMs in all six distance-3 Phase 2B conditions (40 detector checks, 578–586 fault variables, one observable). A preflight showed the 5,000-shot-per-condition plan was well within the runtime cap. The main run sampled 5,000 fresh shots from each original Stim circuit (30,000 total), using the same circuit outcomes for correlation-enabled PyMatching and BP+LSD. All decoders used the same `decompose_errors=True`, `approximate_disjoint_errors=0.0018` decoder model. The BP+LSD fault vectors reproduced every observed detector syndrome (0 invalid outputs).

With min-sum BP (scale 0.9, 200 iterations) and LSD order 0, `LSD_0`, `LSD_E`, and `LSD_CS` each produced 321 logical failures, versus 138 for correlation-enabled PyMatching. Each method was worse in all six conditions. The pooled paired LER increase was 0.00610 (0.01070 vs 0.00460); the equally weighted six-condition macro delta was also 0.00610, with a descriptive across-condition t interval of 0.00270 to 0.00950. That interval summarizes these six fixed conditions and is not a population generalization interval. Discordant outcomes were 223 BP+LSD-only failures and 40 PyMatching-only failures. The methods had identical aggregate outputs in this run; no LSD variant showed a benefit at the fixed configuration.

This is a negative, development-only result for one distance, one approximate DEM threshold, and one BP/LSD configuration. It does not establish that BP+LSD is generally inferior, nor does it support integration. The result suggests that simply treating each approximate DEM instruction as a binary fault variable and applying low-order BP+LSD does not improve over the strong correlation-enabled matching baseline on these circuit samples. Possible causes include loopy inference, the categorical-to-DEM approximation, and poor calibration of the binary fault-variable posterior; the run does not isolate these mechanisms. Full condition-level intervals and runtime are in `bplsd_results.json`. The initial analysis artifact lacking the later syndrome-validity check is preserved as `bplsd_first_pass_unverified.json`; all reported counts come from the corrected rerun.

## Empirical two-decoder selector ceiling

From the prior pilot's independently audited counts, uncorrelated and correlated modes disagree on 1,343/720,000 samples. Correlation-only errors are 580, and uncorrelated-only errors are 763. An oracle choosing the correct output on every discordant shot would reduce baseline errors from 3,532 to 2,769, a 21.6% relative reduction ceiling on this observed sample. The actual correlated mode improves by 183 errors, or 5.18% relative. Both modes are wrong on 2,769 same-prediction cases. A selector between these two outputs has no route to fix those cases. This is descriptive development evidence, not a generalization bound; a genuinely new decoder could add complementary corrections.
