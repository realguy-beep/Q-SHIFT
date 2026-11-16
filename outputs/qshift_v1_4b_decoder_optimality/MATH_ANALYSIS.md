# V1.4B Phase 1: what Boff and BoffStatic actually optimize

## 1. The model both decoders assume

The model is the V1.1–V1.3 d=3, 5-round Z-memory circuit with p = 0.003, plus five independent synthetic burst events (`CORRELATED_ERROR(q) X8 X12 X15`, one per MR boundary).

**Background.** Stim turns the circuit noise into a DEM of independent mechanisms i, each with probability p_i, detector set D_i and logical parity λ_i. The DEM uses `approximate_disjoint_errors=True`, which replaces each categorical PAULI_CHANNEL_2 with independent mechanisms. That is an O(p²) approximation shared by every decoder here, including the reference.

**Bursts.** Event j has probability q, a 3-detector signature σ_j and logical flip 0 (all five are logically trivial).

**Observation.** For a background configuration e ∈ {0,1}^N and a burst mask b ∈ {0,1}^5:
- syndrome s = ⊕_i e_i D_i ⊕ ⊕_j b_j σ_j;
- logical ℓ = ⊕_i e_i λ_i (⊕ 0 from bursts).

**The optimal decision (logical-class MAP, also called maximum-likelihood decoding):**

ℓ*(s) = argmax_ℓ  Σ_b q^|b| (1−q)^(5−|b|)  Σ_{e : ∂e = s ⊕ σ(b), λ(e) = ℓ}  Π_i p_i^{e_i} (1−p_i)^{1−e_i}

## 2. What Boff computes

Boff evaluates each of the 32 masks b. It decodes the residual s ⊕ σ(b) with PyMatching (correlations OFF), keeps the solution's edge-weight sum W(b) = Σ_{i∈ê_b} w_i with w_i = log((1−p_i)/p_i) on the matching graph G, and picks:

b̂ = argmin_b [ W(b) + |b| · log((1−q)/q) ],  predicting λ(ê_b̂).

Because −log P(b, e) = const + |b|·log((1−q)/q) + Σ_{i∈e} w_i, this is **exactly the jointly most probable fault configuration (b, e) under the graph model G.** In other words, it is maximum a posteriori *fault* inference (most-probable-error decoding). It is **not** logical-class MAP. BoffStatic is the same objective with q fixed at 0.01125.

The frozen V1.1/V1.2 decoder B (correlations ON) is **neither**. It chooses edges with PyMatching's correlation-reweighted graph but scores them with static weights. Its objective doesn't correspond to any fixed probabilistic model. That mismatch explained V1.2's "smaller-than-true prior wins" anomaly, and the V1.3 cost repair fixed it.

## 3. Approximations separating Boff from ℓ*

| # | Approximation | Where it enters | Expected effect |
|---|---|---|---|
| a | **Degeneracy ignored**: max over e instead of a sum over each logical class | residual matching | Underweights logical classes reachable by many equally likely fault paths. This is the standard MWPM-vs-MLD gap. |
| b | **Mask selection by min, not sum** | the burst enumeration | Ignores probability mass from other masks that predict the same class. Small when one mask dominates. |
| c | **Graph (pairwise) approximation of background** | PyMatching's decomposed DEM | 254 of 448 d=3 mechanisms are hyperedges (Y-type and two-qubit faults touching 3–4 detectors). They are split into edges and charged as *independent* edge pairs, which mis-weights correlated faults and loses X/Z correlation. |
| d | Probability normalization | burst log-odds vs edge log-odds | **Consistent.** Both are log-odds relative to "no fault", so the comparison across masks is a valid likelihood ratio and no constant is missing. |
| e | Burst-event independence across rounds | model | **Exact by construction** (independent per-round events). |
| f | Prior q̂ vs true q | estimator | Small. V1.3 found Coff − Boff = +0.002 pp, CI spanning 0. |
| g | Categorical → independent DEM conversion | Stim | Shared with the reference; O(p²); not addressed here. |

Items a and c are standard sources of matching sub-optimality and plausibly dominate. Item b is cheap to test directly (candidate A). The exact reference R_true covers a, b and c together, so it removes everything except g. Comparisons then attribute the gap:
- R_true vs Boff gives total headroom under the DEM;
- A vs Boff isolates b;
- B (exact at q̂) vs R_true isolates f;
- at q=0, R_true vs uncorrelated matching (which Boff equals there) gives the background-only headroom from a + c.

## 4. Exact inference: feasibility and complexity

`mld.py` computes P(s, ℓ) exactly by variable elimination in detector order. The cost per shot is O(N · 2^(w+1)), where w is the maximum number of simultaneously open detectors.

| d | detectors | DEM mechanisms | hyperedges (>2 det) | width w | table size 2^(w+1) |
|---|---:|---:|---:|---:|---:|
| 3 | 40 | 448 | 254 | **11** | 4,096 |
| 5 | 120 | 1,682 | 1,106 | 28 | 5.4 × 10⁸ |
| 7 | 240 | 3,700 | 2,526 | 53 | 1.8 × 10¹⁶ |

At d=3 the exact decoder runs at about 6.5–8.7 ms/shot in NumPy, so it's practical as a reference and even as a decoder. At d≥5 this elimination order is intractable. A better ordering, or tensor-network contraction along a spatial cut, would lower w, but the cost stays exponential in a cross-section of roughly d² detectors per time-slice. So this is a reference method for d=3, not a scalable decoder.

## 5. Related methods: applicability

This is from background knowledge; citations were not re-verified online this session.

- **MWPM / PyMatching** (sparse blossom), plus correlation reweighting. This is the current baseline family. It finds the minimum-weight error, not the maximum-likelihood logical class, and it is graph-only.
- **Tensor-network MLD** (Bravyi–Suchara–Vargo for code-capacity noise; later generalizations to circuit-level noise). Applicable in principle. At d=3, exact contraction equals what `mld.py` does. At larger d it needs approximate (bond-dimension-truncated) contraction, which gives no tight bound.
- **Belief propagation.** Plain BP is unreliable on circuit-level DEMs because of short cycles and degeneracy. **BP+OSD** and **belief-matching** (BP marginals reweighting a matching graph) are the scalable, correlation-aware options most relevant beyond d=3. None is installed here; the repo's NS series audited BeliefMatching and HAMLD (an approximate hypergraph MLD) source but did not install them.
- **Exact burst-factor enumeration** (Boff's approach). It is exponential in the number of burst events (2^rounds), not in d. It addresses the burst structure but none of the background approximations a and c.
