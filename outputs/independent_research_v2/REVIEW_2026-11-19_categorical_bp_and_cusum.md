# Review: commits `dcfa4dc` (frozen histogram CUSUM) and `6499182` (categorical Bethe diagnostic)

| | |
|---|---|
| **Reviewer** | Claude (Claude Code), at the owner's request, 2026-11-19 |
| **Scope** | The two reports, protocols, results JSON and scripts in `outputs/independent_research_v2/`, plus the code they call |
| **Method** | Source reading, and deterministic re-execution of the categorical Bethe fixtures. No stochastic sampling was rerun |
| **Files changed** | None existing. This note and `review_categorical_bp_fix_check.py` are new |

## Summary

| Commit | Verdict |
|---|---|
| `dcfa4dc` (CUSUM) | **The result stands.** The gate failure is correctly reported. One sample-accounting correction is needed, and two interpretive points are worth adding |
| `6499182` (categorical Bethe) | **The main conclusion is not supported.** `categorical_bp.py` has two implementation defects. They produce the reported "converged but badly wrong" behaviour, and the tree fixture cannot detect either one. The recommendation (loop correction or bounded exact regions) remains plausible, but its evidence must be regenerated with corrected code |

## 1. `dcfa4dc`: frozen histogram CUSUM under shifted Z

**Verified:**
- The protocol is pre-declared.
- The threshold is checked in code against 8.5945561755.
- The seed is fresh (2026111901).
- The bootstrap resamples whole episodes (20,000 replicates, seed 2026111902).
- The stop rule is followed.
- The report's numbers match the results JSON: 1,141 false switches over 4,500,000 monitored shots, which is 25.36 per 100k [23.96, 26.80].
- The gate requires the upper bound to be ≤ 25, so it fails. The report states this accurately.

**Correction: sample accounting.**
- `adaptive_histogram_cusum.sample_scores` builds the d=3, 5-round `z_biased` Q-SHIFT circuit. It then calls `c.compile_detector_sampler(seed).sample(shots=5_000_000)` and scores those detector rows with the learned linear model.
- The "5,000,000 detector-score samples" are therefore **5,000,000 Q-SHIFT circuit shots (detector-only)**.
- The results JSON records `unique_qshift_circuit_samples: 0`, and the report says the cumulative Q-SHIFT count "remains 338,036,200". Both should count these shots, labelled detector-only with no logical outcomes read, so the project-wide sample ledger stays accurate.

**Interpretive points to add:**
- **Boundary selection.** `adaptive_histogram_cusum_calibrated.calibration_pass` accepts a threshold once the shifted-regime streams reach ≤ 25 per 100k. A threshold chosen to sit just at the limit is expected to land near the limit on fresh data, by regression to the mean. The failure is real but marginal: the point estimate is 1.4% over the limit. It is "not shown below 25", not "clearly above".
- **An episode-level figure.** 1,053 of 5,000 episodes (**21%**) had at least one false switch within 900 monitored shots. That is arguably more decision-relevant than the per-shot rate, and could be reported alongside it.

## 2. `6499182`: categorical Bethe tree and loopy diagnostic

**The claim under review** (report, findings and decision):
- BP is exact on the tree;
- it is badly wrong on the loopy toy "despite reporting convergence";
- the loopy error is therefore "likely tied to loopy approximation/topology rather than a general implementation defect".

### Defect A: false convergence on the first pass

In `outputs/independent_research_v1/categorical_bp.py`, `_conditioned_log_partition`:
1. Each iteration computes `updated_check` from the old variable messages.
2. It then recomputes the variable messages from the **old** check messages (`check_to_var`, not `updated_check`), and measures `largest_change` on the variable messages **only**.
3. In iteration 1 the old check messages are their uniform initial value `[1.0, 1.0]`. Every recomputed variable message therefore equals its prior, which is exactly its initial value. So `largest_change == 0` and the loop declares `converged=True` after one pass, on every factor graph.

Every run in `categorical_bp_tree_diagnostic_results.json` shows `"iterations": 1`, consistent with this. The variable messages entering `_log_bethe_partition` are just the priors. **Loopy BP never iterated**, so "BP reported convergence" in the report is an artifact.

### Defect B: check-message indexing mismatch

- Check-to-variable messages are **initialized** as 2-entry lists indexed by parity bit (`[1.0, 1.0]`).
- They are **read** by parity bit: `incoming[bit]` in the variable update, and `check_to_var[...][effects[variable][check][outcome]]` in `_log_bethe_partition`.
- The update builds them as `for bit in effects[variable][check]`. That is one entry **per fault outcome**, a list of length `len(outcomes)`, which is then read back by bit index.
- **On the tree fixture,** every location has exactly two outcomes, `I` (bit 0) and `X` (bit 1), so the outcome index equals the bit and the defect is invisible. That is why the tree "exactness control" passes.
- **On the loopy toys,** locations have 4 outcomes (one-qubit) or 16 outcomes (two-qubit), so the wrong entries are read.

**The tree control as designed cannot detect defect B.** It should include locations with more than two outcomes, and outcomes whose parity bits do not equal their index.

### Re-execution: the same fixtures, the fixes applied in memory only

`review_categorical_bp_fix_check.py` does not modify `categorical_bp.py`.
- **Defect A fix:** include the check-message change in the convergence measure.
- **Defect B fix:** build check messages `for bit in (0, 1)`.

| Fixture (outcomes per location) | Variant | Exact MAP risk | Bethe MAP risk | Max posterior error | Iterations | Converged |
|---|---|---|---|---|---|---|
| tree (2) | as written | 0.26 | 0.26 | 0.0 | 1 | yes |
| tree (2) | both fixed | 0.26 | 0.26 | 0.0 | 34–35 | yes |
| one-qubit (4) | as written | 0.002646 | **0.057354** | **0.566** | 1 | "yes" |
| one-qubit (4) | indexing only | 0.002646 | 0.057354 | 0.566 | 1 | "yes" |
| one-qubit (4) | **both fixed** | 0.002646 | **0.002646 (exact)** | 0.206 | 200 (cap) | **no** |
| two-qubit (16) | as written | 0.060 | 0.060 | 0.260 | 1 | "yes" |
| two-qubit (16) | indexing only | 0.060 | 0.060 | 0.212 | 1 | "yes" |
| two-qubit (16) | both fixed | 0.060 | 0.060 | 0.468 | 200 (cap) | **no** |

The "as written" rows reproduce the committed results exactly. Applying only the defect A fix crashes (`IndexError`), because the per-outcome check messages are then compared against 2-entry initial messages. That crash is how defect B surfaced.

### Consequences

1. **The one-qubit MAP failure disappears with corrected code.** The reported risk of 0.057 against an exact 0.0026 is an implementation artifact, not a Bethe limitation. The conclusion "loopy approximation/topology rather than a general implementation defect" should be withdrawn.
2. **A genuine loopy problem remains, of a different kind.** With both fixes, BP **does not converge** on either loopy toy: it oscillates, at damping 0.5, through the 200-iteration cap. Its conditional probabilities are poorly calibrated (maximum errors 0.21 and 0.47).
   - This review does not establish why: whether the cause is short cycles, damping applied only to variable messages, or the Bethe approximation itself.
   - Partition estimates from non-converged messages should not be treated as Bethe fixed-point values.
3. **The decision to keep the loopy decoder stopped before circuit evaluation is still correct.** The redirection to loop correction or bounded exact regions is still reasonable. Before that work, a corrected `categorical_bp.py` and a strengthened tree control (multi-outcome locations) are needed, and the loopy diagnostic should be re-run and re-reported.

## Reproduction

```bash
python outputs/independent_research_v2/review_categorical_bp_fix_check.py
```

- Deterministic exhaustive enumeration.
- No stochastic or circuit samples.
- It asserts that the reviewed source lines are unchanged before patching them in memory.
