# Gate 3A Independent Audit — Partial Stop

**Audit status: PARTIAL; source-dependent work stopped.** This is not a full Gate 3 result. `ORIGINAL_48_FILE_RETRIEVAL_COMPLETE` remains `FALSE`.

## Executive result

The supervisor amendment at `7b55433cca8a66a35434da56cc4c524766f0da91` authorizes a bounded deterministic audit and specifies strict stop conditions. While locating its exact files, I mistakenly used a recursive Git path listing. It surfaced unrelated Stage 5 pathnames. No files at those paths were opened; no contents, results, labels, or hashes from them were inspected. The amendment expressly requires stopping affected tasks on out-of-scope filename/content exposure. I stopped circuit/source-semantics work and did not attempt to retrieve or inspect any Stage 5 item.

Thus C1 is **UNVERIFIED**; I did not independently reconstruct circuit identity, detector ordering, fault supports, or observable parity. Claims depending on that map (Q-SHIFT application of C2, C3, C5, C6, C7) are not accepted as circuit-level results. Abstract proofs independent of C1 are recorded below. No source was executed; no tests, Stim operations, sampling, simulation, decoder evaluation, or sealed-outcome access occurred.

The amendment's scope is scientifically coherent, and selected conditional mathematics can be checked. The source-dependent certificate is **not independently verified**. Full Gate 3 remains HOLD. Supervisor review of the pathname-only incident is needed before any new C1 attempt.

## Evidence and scope

- Scientific pin: `5c8f8391491427fab16845282a5c8c540746b145`.
- Scope amendment and claim matrix: `7b55433cca8a66a35434da56cc4c524766f0da91`.
- Reconciliation memorandum: `b4d55fa23c9cc3a3664375437c74243d40cc3ddc`.
- Prior independent scope review: `e9b569473234094934f488a54836bc535f49aff1`.
- The amendment permits only existing snapshot/pinned evidence, prohibits substitutes/retrieval, and preserves the 48-file incomplete flag. The canonical manifest bytes and per-path rationale remain unavailable in the earlier evidence record.
- Reviewed NS-5A paths and pinned manifest hashes are listed in `EVIDENCE_AND_HASH_MANIFEST.json`.

### Scope incident

The command used to locate amendment-related paths was:

```text
git ls-tree -r --name-only 7b55433cca8a66a35434da56cc4c524766f0da91 | Select-String 'gate3a|scope_amend|claim|manifest|C5|C4'
```

The recursive listing returned unrelated Stage 5 pathnames because the filter included the generic word `manifest`. This was pathname-only exposure; no file content was opened. The broad listing stopped. This report does not repeat the names. C1 and its source-dependent descendants were stopped. Work continued only on exact amendment/NS-5A paths named in the amendment or pinned NS-5A manifest. No later broad listing was made.

## C5 rank-definition correction

The amendment matrix says “rank-2 identifiability for 45-feature mean map” but does not specify the two free parameters, point, scales, Jacobian, or threshold. In contrast, the pinned NS-5A `CLAIM_EVIDENCE_MATRIX.md` and its named result specify a **three-parameter** burst/measurement/gate model:

- Feature vector: 40 detector marginals `E[D_i]` for detector IDs 0–39 and five pair cofire means for `(8,10)`, `(16,18)`, `(24,26)`, `(32,34)`, `(36,38)`.
- Free parameters `(p_b,p_m,p_g)` and nominal point `(.010,.003,.003)`; declared scales `(.008,.004,.001)`.
- Whitened/scaled central finite-difference Jacobian shape `45×3`; steps `1e-4`, `5e-5`, `2.5e-5`; numerical rank threshold relative to largest singular value `1e-8`.
- Saved exact-categorical singular values `.2977118122, .1699153002, .1072531200`, reported numerical rank **3**.
- A separate approximate-DEM result also reports `45×3`, rank **3**, at the same nominal coordinates but for a different mean model (591 mechanisms).

These are pinned numerical findings, not independently recomputed here: C1 could not pass, so the feature/support map was not independently reconstructed. They do not establish exact symbolic rank, global identifiability, finite-history recovery, or estimation accuracy. A two-parameter restriction (for example, fixing gate noise) is a different Jacobian. No such point/rank calculation is specified in the C5 evidence reviewed. Correct C5 to identify the three-parameter numerical-rank-3 result and list any two-parameter result separately as unspecified/unverified. Do not silently treat the two models as equivalent.

## Conditional independent derivations

### C2 — parity-character identity

For independent categorical sites `j`, mutually exclusive outcomes `o`, probabilities `p[j,o]`, and detector mask `S[j,o]`, outcome sign on parity set `A` is `(-1)^|A∩S[j,o]|`. Averaging at each site and multiplying by site independence gives `χ(A)=∏_j Σ_o p[j,o](-1)^|A∩S[j,o]|`. From `(-1)^D=1−2D`, `E[D_i]=(1−χ_i)/2`; from `(-1)^(D_i+D_k)=1−2D_i−2D_k+4D_iD_k`, `E[D_iD_k]=(1−χ_i−χ_k+χ_ik)/4`. This proves the identity under the categorical factorization, not the correctness of Q-SHIFT masks. The theorem is established under assumptions; C2 as a Q-SHIFT claim is UNVERIFIED because C1 is unresolved.

### C4 — edge-moment inversion and exact path

The pinned NS-5A source manifest names `outputs/qshift_method_landscape_research_v1/published_edge_moment_inversion_audit.py`, SHA-256 `E52963B664A2E09C18F3102D616C02155BDF0180E84EEF3E316EF3EE0D8EB845` (8,218 bytes). The local file hash matched. This resolves the path through the pinned manifest; it does not establish that the file was in the separate 47-file connector snapshot.

For the abstract model `D_i=A XOR E`, `D_j=B XOR E`, with independent Bernoulli rates `a,b,p`, set `α=1−2a`, `β=1−2b`. Then `χ_i=α(1−2p)`, `χ_j=β(1−2p)`, and `χ_ij=αβ`; the shared event cancels in pair parity. With means `m_i,m_j` and cofire `q`, `χ_ij=1−2(m_i+m_j)+4q` and `q−m_im_j=(χ_ij−χ_iχ_j)/4=χ_ij p(1−p)`. When `χ_ij≠0`, the ratio is `p(1−p)`; the lower-branch inverse is `p=1/2−sqrt(1/4−(q−m_im_j)/χ_ij)` for `0≤p≤1/2`. The inverse is not unique over all `[0,1]`; it requires a real radicand in `[0,1/4]`, nonzero denominator, independence/factorization, and branch restriction. It estimates an effective edge probability, not general physical burst cause. Saved grids were not rerun. C4 is conditional.

### C8 — e-factor

For `X_t∈[0,1]`, fixed `m0>0`, and fixed `λ∈[0,1]`, `L_t=1+λ(X_t/m0−1)` has minimum `1−λ≥0`. If `E[X_t|F_(t−1)]≤m0`, then `E[L_t|F_(t−1)]=1+λ(E[X_t|F]/m0−1)≤1`. With adapted, integrable increments this yields a nonnegative supermartingale; Ville gives `P(sup_t M_t≥1/α)≤α`. The conditional mean must hold at every time, not just marginally. The theorem is valid under its assumptions; no actual circuit/DEM/device conditional law was verified. C8 is CONDITIONAL.

### C9 — mixture recurrence and threshold

`w_s=1/[s(s+1)]=1/s−1/(s+1)`, so the prior sums to one and its tail after `t` is `1/(t+1)`. For `A_t=Σ_{s≤t}w_s∏_{i=s}^tL_i`, factoring out `L_t` gives `A_t=L_t(A_(t−1)+1/[t(t+1)])`; the full mixture is `E_t=A_t+1/(t+1)`. Under C8, fixed mixture components preserve the nonnegative-supermartingale property. Ville threshold is `1/α`; at `α=.05`, it is 20. The checkpoint correction states the historical predicate tested `E≥.05`, not `E≥20`; corrected comparison `lower*α_num ≥ scale*α_den` is algebraically equivalent to the right threshold. The reported 239 upward/0 downward distinct-prefix counts were not rerun; they are fixture counts, not error probabilities. C9 is CONDITIONAL on C8; count reproduction UNVERIFIED.

### C10 — fixed-point direction

For nonnegative factors, weights, tails, and products, rounding each downward at scale `Q` preserves a lower bound by monotonicity and induction. Such a bound cannot create a threshold crossing absent from the exact mixture, though it can suppress a true crossing. The correction report says Python arbitrary-precision integers were used and an upward fixture intermediate reached 199 bits; I did not reproduce that maximum. Fixed-width overflow, persistence, and deployed implementation safety remain unverified. C10 is conditional for abstract rounding and unverified for implementation safety.

### C11 — Freedman delay form

Suppose `W_i=log L_i∈[a,b]`, `E[W_i|F_(i−1)]≥μ>0`, `Var(W_i|F_(i−1))≤v`, and `|W_i−E[W_i|F_(i−1)]|≤c`. Freedman’s lower-tail inequality gives for `nμ>A`:

```text
P(log M_n < A) ≤ exp(−(nμ−A)^2 / (2(nv+c(nμ−A)/3))).
```

Use `A=log(1/α)` for a fixed start. In the one-change mixture, `E_t≥w_sM_t^(s)`, so component crossing at `1/(αw_s)` uses `A_s=log(1/(αw_s))`. This is a sufficient conditional crossing-delay bound, not expected delay or observed latency. The saved package has an earlier Azuma range-only table and a later Freedman/Bhatia–Davis variance-aware table: for upward `α=.05,δ=.10`, saved values are respectively 69,239 and 10,433 shots. These are different inequality constructions, not a direct contradiction. Numeric rows were not independently recalculated; C11 remains CONDITIONAL and numeric reproduction UNVERIFIED.

## C12 — controller abstraction

The written specification implies only abstract invariants: completed shot `t` may first affect shot `t+1`; no logical label or true parameter enters the online decision; alarm causes static abstention rather than new parameter/graph selection; validated static decoding continues during recalibration; new trusted state requires external verification and a future block boundary. The document says no runtime controller is implemented. Reset authority, alpha reuse, latency, persistence, complete transition edges, and repeated-switch guarantee remain unspecified. C12 is CONDITIONAL for these text-level invariants and UNVERIFIED for transition completeness, implementation conformance, operational safety, and utility.

## Separate validity axes

- **Mathematics:** C4/C8/C9/C10/C11 statements hold under their written assumptions.
- **Numerical reproduction:** no rank, 468-coefficient, delay-row, fixture-count, or 199-bit maximum calculations were rerun here.
- **Circuit/source fidelity:** C1 stopped; dependent claims remain unverified.
- **Conditional statistical validity:** C8–C11 require conditional premises; none was verified for DEM/device streams.
- **Decoder utility:** excluded and unverified. No LER/performance claim is made.

Exact-circuit-to-DEM transfer remains excluded. An alternative lower-envelope violation alone does not prove null invalidity; a DEM requires its own null and alternative analysis under separate authorization.

## Recommendation

Do not accept C1 or any dependent source/certificate claim. Preserve the conditional C4 and C8–C12 conclusions and the C5 correction. Seek supervisor disposition on the pathname-only scope incident before any new C1 attempt. No Gate 3A execution or full Gate 3 completion is declared.
