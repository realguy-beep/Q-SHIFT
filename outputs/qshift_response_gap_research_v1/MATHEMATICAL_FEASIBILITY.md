# How fast could the response be?

## Causal floor

Let c be the first changed block. In AD2/AD3, the action for t is measurable with respect to observations through t−1. Compare a history that stays in the old state to one that first changes at c with the same history through c−1. Without an advance signal, the action at c has the same conditional distribution in both paths. An unannounced transition cannot be reliably detected with zero *post-change* observations. A logged alarm at index c is usable for action c+1, the first possible reactive action on the present interface. Acquisition and return to low logical loss may take longer. AD3 reaches c+1 in 10/24 S2 events by its historical support/release criterion, including some flag releases. This establishes feasibility in some events and leaves reliable first-block action unresolved. [Q2, Q4, Q6](REFERENCES.md#q-shift-evidence)

Sub-block response is a separate interface comparison. An action after a prefix of c may affect only subsequent evaluation rows. That requires a simulator path with ordered observation timestamps, the subsequent decoder ready on time, and any observable calibration labels actually delivered by that cutoff. Feeding a full block average to a controller and revising predictions on the same rows would violate the current scientific chronology. A pulse that ends before a usable prefix can contribute evidence but yields no exposure for a useful in-pulse switch. With a mean statistic and changed fraction f of the prefix, its expected change is f times the all-changed mean difference under a two-state mixture. That attenuation is arithmetic, independent of algorithm. Transient detection literature targets misses during a finite window [E6](REFERENCES.md#primary-literature).

## A necessary fixed-horizon information check

Fix a common pre-change history, a null observation law P0, an alternative P1 and a decision event A by a fixed time. The map from observations (and independent randomization) to 1(A) gives, by data processing,

\[
D(P_1\Vert P_0)\ \ge\ d(\Pr_1(A)\Vert\Pr_0(A)),\qquad
d(a\Vert b)=a\log(a/b)+(1-a)\log((1-a)/(1-b)).
\]

For a test with false probability ≤α and detection ≥β>α, the right side is at least d(β‖α). For conditionally IID rows under a fixed simple pair the joint KL for n rows is nD(row1‖row0). Otherwise use joint prefix KL, or the chain rule for conditional increments. The condition also holds for a correct action event against each relevant competing state, including a wrong alternative or OFF. For a one-look likelihood test the Neyman–Pearson ROC of the specified models would give attainable power. Composite states, overlapping looks, and a fitted reference change the problem. [E7](REFERENCES.md#primary-literature)

| Illustrative fixed-look target | Required prefix KL (nats) | Per row if IID, n=2,000 | Per row if IID, n=500 |
|---|---:|---:|---:|
| α=.01, β=.90 | 3.820575 | .00191029 | .00764115 |
| α=.01, β=.95 | 4.176899 | .00208845 | .00835380 |

These targets are mathematical illustrations, not AD3's empirical per-comparison tail or the proposed episode-level gate. The AD3 statistic sums marginal detector fits and re-estimates pre and post rates. Its scale, footprint, and threshold do not give joint KL or effective independent detector count. In a simple IID persistent-change model the classic large-ARL CUSUM scale is log(ARL)/I with I the true post-change expected log likelihood ratio per look. It does not convert this G into a Q-SHIFT delay estimate. [Q2, Q7](REFERENCES.md#q-shift-evidence) · [E1](REFERENCES.md#primary-literature)

### A finite-row bound for S2

For matched background and fixed past, let P be a detector row under OFF and Q the row under ON. Conditional on no extra burst fault, ON generates the OFF row law. The candidate circuit inserts five independent Bernoulli opportunities at q=.01, so Q=wP+(1−w)R with w=.99⁵. For n independent post-change rows Qⁿ dominates wⁿPⁿ as measures. Therefore an OFF→ON alarm with Pⁿ(A)≤α has Qⁿ(A)≤1−wⁿ(1−α). An ON→OFF alarm with Qⁿ(A)≤α has Pⁿ(A)≤min(1, α/wⁿ). These inequalities also cover statistics of those rows and, if supplied from the same fresh row law, their calibration observables. Include every fresh observation used in n. The bound does not use the oracle decoder or assume every injected fault is observable. [Q5](REFERENCES.md#q-shift-evidence)

| Fixed-horizon α=.01 | Required rows ON | Required rows OFF |
|---|---:|---:|
| β=.90 | ≥46 | ≥90 |
| β=.95 | ≥60 | ≥91 |

For example the ON bound is n≥ceil(log[(1−β)/(1−α)]/log w). The OFF bound is n≥ceil(log[α/β]/log w). Both are optimistic necessary conditions, since R can resemble P. They exclude instant high-confidence switching and allow plenty of room for a 500- or 2,000-row look. They establish neither reliable sub-block action nor an impossibility at those sizes. The matched background requirement excludes S3 as recorded.

### Distinguishability and missing measurements

A separate d=5 algebraic preflight could reconstruct the categorical Pauli fault sites and parity supports. For a fixed mod-2 detector mask a, the parity moment is the product over independent sites j of \(1-2\sum_{f:\langle a,v_{jf}\rangle=1}p_{jf}\), where alternatives f at site j are disjoint. With validated burst masks v_r, ON multiplies the OFF moment by \(\prod_{r:\langle a,v_r\rangle=1}(1-2q)\). Means and cofires follow from moments of one and two bits. That gives projected feature contrasts and, for small subsets, exact marginal laws by Walsh inversion. It cannot prove full-distribution separation from a few moments. An approximate DEM should be analyzed as its own law. In particular, detector-equivalent classes with different logical effects cannot be identified by detector observations alone if their full detector laws agree. Additional timely calibration labels or a robust action spanning that ambiguity are then necessary. [Q5, Q9](REFERENCES.md#q-shift-evidence) · [E6](REFERENCES.md#primary-literature)

To estimate one-block feasibility, collect on separate development roots the joint prefix-feature covariance/likelihood, conditional null tails with actual resets, and a confusion table for benign background changes, weak burst ON, weak burst OFF and novel supports. Compare detector-only selection and selection with the original labelled budget in matched splits. Stratify empirical power by state pair and observation count. Per-shot distribution or calibrated projection evidence is needed for design. Archived marginal G, accepted classes and LER alone cannot establish a reliable delay lower bound beyond the causal and mixture arguments above.

## How faster switches can raise logical loss

For two states and a fixed horizon, let B be the improvement in logical risk from switching when the new state is true, and C the extra risk when the old state is true, with B,C>0. If p is the calibrated probability of the new state and κ a switch cost expressed in equivalent loss units at that horizon, switch only when pB−(1−p)C>κ, or p>(C+κ)/(B+C). For a single decision with change prior π, detection probability β and false probability α, improvement before direct switching cost is πβB−(1−π)αC. Frequent looks and state-dependent hold/return rules affect both π and the realized cost. Even accurate detectors can deliver little LER benefit if the decisions rarely change logical predictions, or if those changes do not agree with labels. Estimate R(state, action) and paired disagreement using a separate development policy split. Use a conservative fallback for an ambiguous state or poor worst-case risk. The large ON cost and smaller OFF cost in S2 describe the historical policies and do not identify alternative decoder risks. [Q3, Q4](REFERENCES.md#q-shift-evidence)

An e-detector could add null control once conditional expectation bounds hold under every active null history, including adaptive reference and reset state. A first-alarm ARL result, a fixed-horizon probability and a repeated-switch budget are different objects. Optional-stopping validity for each fixed process does not automatically cover restart or reuse. Existing NS-5B work derives assumption-level results for a different model and did not validate correspondence or guarantees for this d=5 stream. Start with empirical episode-separated operating characteristics and a finite horizon. [Q9](REFERENCES.md#q-shift-evidence) · [E8](REFERENCES.md#primary-literature)
