# Correlated decoder V1.2: design plan (DRAFT, not frozen)

**Status:** planning draft for owner review. No code, seeds, freeze or sampling yet. Nothing here authorizes execution.

## Why V1.2

V1.1 is INCONCLUSIVE: all 60,000 evaluation shots were committed, but finalization failed on an analyzer key mismatch (fixed in `outputs/qshift_correlated_decoder_v1_1_analyzer_fix_v1/`). The recovered descriptive numbers favoured B (five-factor) over A by 0.39 pp. V1.1 cannot answer the project's open question, though, for two reasons:

1. **A is not a strong static baseline.** A is PyMatching fixed at the pooled detector-only estimate q̂≈0.0102. Nothing selected it to minimize LER. At q=0 it lost to A2 by 0.35 pp (1.060% vs 0.710%), so part of B−A is plausibly A's mis-tuning rather than B's merit. This is the same weak-comparator problem Stage 5 had.
2. **Representation and adaptation are confounded.** B differs from A both in model (five-factor enumeration vs matching) and in calibration scope (per-root vs pooled). V1.1 had no static five-factor arm to separate the two.

V1.2's single question: **does the five-factor representation beat the best static matching decoder on fresh data, and is any gain from representation or from per-root adaptation?**

## What stays fixed (no change from V1.1)

- Circuit: rotated d=3 Z-memory, 5 rounds, p_gate = p_meas = 0.003, `CORRELATED_ERROR(q) X8 X12 X15` after each of 5 MR boundaries; q ∈ {0, 0.01, 0.02}.
- Estimator: the frozen V1.1 affine cofire estimator (fit on V1 training detector rows, corrected coefficient order). **No refit.**
- Decoder implementations: `model.py` `BurstEnumerationDecoder` and `build_matching` unchanged. They are imported by hash, not copied and edited.
- Statistics family: root-stratified paired percentile bootstrap, 20,000 replicates, NumPy `linear` quantiles.

## Arms

| Arm | Definition | Role |
|---|---|---|
| A0 | PyMatching at q=0 (nominal) | Informational; Stage 5-style comparator |
| A | PyMatching at pooled calibration q̂ (V1.1 definition) | Continuity with V1.1 |
| **A\*** | PyMatching at the static q selected on the selection set (below) | **Strong static baseline** |
| A2 | PyMatching at per-root q̂ | Adaptive matching |
| B_static | Five-factor at the static q selected on the selection set | Representation without adaptation |
| **B** | Five-factor at per-root q̂ | Candidate |
| C | Five-factor at true q | Privileged reference, not deployable |

All arms decode identical detector rows per root. Labels are read only after every arm has predicted.

## Static selection (before any V1.2 sampling)

- **Selection set:** the 60,000 committed V1.1 evaluation shots (`attempt_001`, 30 archives), read-only and hash-verified. They are already-exposed development data. They are disjoint from all V1.2 evaluation seeds and used only to pick A\* and B_static. This costs zero new shots. The V1.1 run directory is never written.
- **Grid:** q ∈ {0, 0.0025, 0.005, …, 0.02} (9 points), plus V1.1's pooled q̂ = 0.0101667.
- **Criterion:** the minimum equal-weight mean LER over the three conditions; ties go to the smaller q. This is done separately for matching (→ A\*) and five-factor (→ B_static). A minimax variant is reported descriptively only.
- The selected values are written into the V1.2 pretest freeze **before** any V1.2 seeds are sampled.

## New allocation

| Partition | Roots | Shots/root | Shots |
|---|---|---|---|
| Per-root calibration (detector-only) | 3 q × 24 | 500 | 36,000 |
| Paired evaluation | 3 q × 24 | 4,000 | 288,000 |
| **Total new** | | | **324,000** |

**Sizing rationale (planning only):** V1.1's per-root SD of paired differences was about 0.0016 to 0.0028 at 2,000 shots/root. At 4,000 shots and 24 roots per q, the primary SE is about 2.5×10⁻⁴. That gives roughly 80% power to exclude zero for a true effect of 0.07 pp. The gap against A\* is expected to be smaller than V1.1's 0.39 pp against A, so the 10-root V1.1 design would be underpowered.

**Runtime:** B+C cost about 1.3 ms/shot in V1.1, and B_static adds about 0.7 ms/shot, so roughly 600 s for evaluation inference. Proposed wall cap: 1,800 s, with the preflight projection required to stay under 60% of the cap.

Seeds come from a new V1.2 namespace, screened for collisions against the V1, V1.1 and earlier development inventories. No Stage 5 or sealed data is read.

## Endpoints and decision rule

**Co-primary** (equal-weight mean over q = 0.01 and 0.02 of root-paired LER differences; negative favours B):

1. B − A\* (beats the strong static matching baseline)
2. B − A2 (beats adaptive matching with the same per-root information)

This is an intersection-union test: GO needs both, so no multiplicity correction is applied.

- **GO (development only):** both two-sided 95% intervals entirely below 0; at least 100 A\* errors pooled over nonzero q; B point LER below A\* at both nonzero q; and the q=0 one-sided 95% upper bound for B − A\* below +0.0005.
- **NO-GO:** the B − A\* interval is entirely at or above 0, or the q=0 one-sided 5% lower bound for B − A\* is above +0.0005.
- **INCONCLUSIVE:** everything else, including incomplete evidence or any gate/finalization failure.

**Secondary / descriptive:** B_static − A\* (representation alone), B − B_static (value of adaptation), B − A0, B − A, C − B, prediction disagreements, and estimator bias/MAE.

**Interpretation boundary:** even a GO is development evidence for one synthetic three-qubit mechanism at d=3. B also knows the burst support exactly. It is not hardware, scaling or independent-test evidence.

## Engineering safeguards (lessons from V1 and V1.1)

- **End-to-end finalization rehearsal.** Before freeze, run the full runner → analyzer → manifest path on a fake sampler (synthetic detectors), so the interface defect class that broke V1.1 is caught. Required test: the analyzer reads every key the runner writes, checked from shared constants rather than duplicated string literals.
- Use the fixed analyzer pattern: validate all metadata before writing any output, and write to a dedicated output directory.
- Keep V1.1's watchdog, `--expected-head` launch, refusal to resume or retry, and partial-evidence preservation.
- Calibration batches are stored detector-only; observables are not persisted for calibration partitions.

## Steps once approved

1. Draft the frozen protocol, config and code for selection, runner, analyzer and rehearsal on this branch. Sampler-free tests only.
2. Run the static selection on the V1.1 arrays (no sampling), record A\* and B_static q, and commit.
3. Generate seeds, run preflight and rehearsal, then commit the pretest freeze.
4. With owner sign-off, run the single bounded evaluation (324,000 shots).
5. Finalize, run an independent saved-array audit, and report GO/NO-GO/INCONCLUSIVE.

## Decisions for the owner

1. Is reusing the V1.1 evaluation arrays as the static-selection set acceptable? The alternative is about 60,000 fresh labeled selection shots.
2. Are 24 roots × 4,000 shots (288,000 evaluation shots) and an 1,800 s cap acceptable?
3. Is the co-primary rule acceptable: GO requires beating both A\* and A2?
