# Independent mathematical audit

## Scope

The audit reads the 139-file method-landscape package and the explicitly referenced circuit/noise-generator source needed to interpret its formulas. The checkpoint ledger and source/result pairs were used to locate and classify claims; central claims were independently reconstructed below where tractable. This work uses exact algebra, saved deterministic artifacts, and the new bounded rational recurrence audit. It did not call a Stim sampler, generate detector shots, run a decoder, train a model, or inspect sealed outcomes.

## Exact categorical feature law

Assume independent categorical fault sites indexed by `j`, with mutually exclusive outcomes `o` and probabilities `p[j,o]`; each outcome has detector mask `s[j,o]`. For a detector subset `A`, define its parity character `chi(A)=E[(-1)^(XOR_{i in A} D_i)]`. Independence across sites yields

```text
chi(A) = product_j sum_o p[j,o] (-1)^(|A intersect s[j,o]|).
```

Thus `E[D_i]=(1-chi({i}))/2` and `E[D_i D_k]=(1-chi({i})-chi({k})+chi({i,k}))/4`. This derivation is exact under site independence and correct fault-to-detector supports. The package's independent direct-XOR implementation agrees with the character calculation to about `3.84e-15` at the saved point, but both share the same deterministic support map; this is not an independent validation of Stim's circuit semantics. The source maps alternatives by inserting Pauli operations into a noiseless reference circuit and explicitly expects 40 detectors and one observable. The proof does not apply unchanged to correlated faults across sites, unknown circuit changes, or a different DEM approximation.

## Five burst-pair signatures

For the documented distance-3, five-round z-memory synthetic circuit, the simulator inserts one `CORRELATED_ERROR(p) X8 X10` after each `MR` boundary. The saved deterministic fault map reports detector supports `(8,10)`, `(16,18)`, `(24,26)`, `(32,34)`, `(36,38)`. The source asserts these exact signatures and the persisted feature artifact records them. This supports a source- and circuit-specific deterministic mapping claim. It does not show that the synthetic common-cause fault is hardware-calibrated, or that those detector supports are universal across bases, rounds, generators, or noise mechanisms.

## Edge-moment inversion

Under the independent-edge model, let a shared Bernoulli edge `E~Bernoulli(p)` toggle two endpoints, while independent boundary events toggle each endpoint. If endpoint bits are `D_i=A XOR E`, `D_j=B XOR E`, then the parity expectations satisfy `chi_i=(1-2a)(1-2p)`, `chi_j=(1-2b)(1-2p)`, and `chi_ij=(1-2a)(1-2b)`. With marginals `m_i,m_j` and cofire `q`, `1-2(m_i+m_j)+4q=chi_ij` and `q-m_i m_j=chi_ij p(1-p)`. Therefore the cited inversion returns `p` on the lower branch `0<=p<=1/2`.

That derivation is proven for the stated independent-edge graph model. The Q-SHIFT package applies it to an exact categorical circuit and an approximate DEM on saved deterministic grids (405 pair rows); those are numerical model-specific checks, not a theorem for arbitrary circuit noise. The saved maximum errors are near floating-point roundoff. I did not regenerate that grid. The inversion estimates an effective shared-edge probability only when its independent-edge factorization and branch assumptions hold; it cannot establish physical cause attribution under a nuisance producing the same detector masks.

## Three-parameter identifiability

The saved exact-circuit 45-feature map has a 45-by-3 finite-difference Jacobian at `(p_b,p_m,p_g)=(.010,.003,.003)` with reported whitened scaled singular values approximately `.2977,.1699,.1073` and numerical rank 3. The finite difference columns are stable over the listed step halvings. This is numerical local-rank evidence at one operating point (with a separate finite grid), not an exact symbolic rank certificate, global injectivity, finite-history estimator accuracy, or robustness to an unknown correlated-readout nuisance. A matched-mask nuisance can make physical cause nonidentifiable even when the declared three-parameter map is locally full rank.

## Continuous nuisance envelopes

The three-parameter exact-circuit source constructs rational univariate character polynomials for burst, measurement and gate rates, then uses tensor Bernstein coefficients over the declared rectangles. The convex-hull property of Bernstein bases makes the min/max coefficient bounds valid for a polynomial on a rectangle, provided the support map is fixed and the polynomial construction exactly represents the generator. The saved exact bounds put low-region `X` upper at `.0030064726213` and high-region lower at `.0099030715233`, a certified gap about `.0068965989020`; eight direct feature-mean probes agree to reported absolute error at most `1.02e-16`. I reviewed the rational arithmetic and bounding construction but did not independently regenerate all 468 coefficients. The certificate's own scope is exact categorical circuit, independent per-site noise, and its specified rectangular parameter bounds. It is not a DEM certificate.

## One-sided e-factor validity

For `X_t in [0,1]`, fixed `m0>0`, and `0<=lambda<=1`, `L_t=1+lambda*(X_t/m0-1)` is nonnegative. If under the null `E[X_t | F_(t-1)]<=m0`, then `E[L_t | F_(t-1)]<=1`. Products are nonnegative supermartingales, and Ville's inequality controls `P(sup_t M_t >=1/alpha)<=alpha`. This is a mathematical conditional result. It requires the conditional mean envelope to hold given the complete past, not merely as a marginal population mean. The exact-circuit continuous-rectangle certificate can supply such a bound only if per-shot noise parameters remain in that declared model/rectangle conditionally. The package does not establish this for the approximate DEM, an actual device, or an adaptive adversary outside the assumptions.

## One-change mixture recurrence and checkpoint 133

The prior `w_s=1/[s(s+1)]` telescopes to one. At time `t`, the mass assigned to not-yet-started components is `1/(t+1)`. With `A_0=0`,

```text
A_t = L_t (A_(t-1) + 1/[t(t+1)]),  E_t=A_t+1/(t+1).
```

This identity is exact by induction and equals the direct component sum. The saved checkpoint-133 alpha predicate was wrong; the corrected independent arithmetic is in `efactor_threshold_audit_v1.py`. For alpha `.05`, the threshold is 20. Under the bounded six-category factor table and four-step horizon, corrected fixed-point lower-bound hits are 239 distinct upward prefixes and zero downward prefixes (244 upward hits in the historical repeated-suffix loop). These are not statistical false-alarm frequencies.

## Analytic detection-delay bounds

The saved delay derivation bounds log increments in a finite interval, lower-bounds their conditional mean under a sustained alternative, upper-bounds conditional variance with Bhatia–Davis, and applies a one-sided Freedman lower-tail inequality. For the one-change mixture it adds the component penalty `log(1/(alpha*w_s))`. This yields sufficient post-change shot counts at a stated crossing probability bound under the exact model and conditional-alternative assumptions. It is not an expected delay, observed delay, trajectory simulation, or claim about within-circuit measurement-round latency. The formula and assumptions are coherent as a conditional concentration argument, but the full numeric table and outward-rounded implementation were not independently recalculated in this audit. No adaptive action or decoder benefit follows from the delay certificate.

## Exact circuit versus approximate DEM

The categorical circuit distribution and the Stim DEM produced with `decompose_errors=True, approximate_disjoint_errors=True` are different probability models. At the saved nominal point their 45 feature means differ by up to `3.27e-5`. The saved finite DEM-transfer screen contains one high-alternative point outside the exact-circuit continuous lower envelope (`p_b=.010,p_m=.001,p_g=.002`); it is only a 250-point screen, not a continuous DEM counterexample proof, but it is enough to reject an unqualified transfer of the exact-circuit envelope. Exact categorical bounds cannot be represented as a DEM guarantee without a separate proof.

## Mathematical disposition

Core identities are correct under their written assumptions. Checkpoint 133's crossing calculation was not valid and is corrected only in this new version. Several computational certificates remain conditional on support mapping and source-to-polynomial construction, and selected quantitative results were not independently regenerated. No result establishes decoder performance, physical noise attribution, or controller safety. For this package, the defensible decision is **CORRECTIONS_REQUIRED**; autonomous controller readiness is separately **HOLD**.
