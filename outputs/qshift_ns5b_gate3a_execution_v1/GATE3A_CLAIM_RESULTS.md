# Gate 3A Claim Results

Scientific pin: `5c8f8391491427fab16845282a5c8c540746b145`. Amendment: `7b55433cca8a66a35434da56cc4c524766f0da91`.

| Claim | Status | Mathematics | Numerical reproduction | Source/model fidelity | Conditional statistics | Decoder utility |
|---|---|---|---|---|---|---|
| C1 identity/order/support/observable | **UNVERIFIED** | Not evaluated | Not evaluated | Independent reconstruction stopped after scope trigger | N/A | Excluded |
| C2 parity/moments | **UNVERIFIED for Q-SHIFT; identity conditional** | Formula derived under independent categorical sites | No hand-case execution | Q-SHIFT application depends on C1 | Only under factorization | Excluded |
| C3 five burst signatures | **UNVERIFIED** | N/A | Not reproduced | Depends on C1 | N/A | Excluded |
| C4 edge inversion | **CONDITIONAL** | Derived for stated independent-edge model | Grid values not rerun | Effective graph model only | N/A | No inference |
| C5 local rank | **UNVERIFIED** | Exact rank not established | Saved numerical rank reviewed, not recomputed | Depends on C1 | N/A | Excluded |
| C6 exact polynomial | **UNVERIFIED** | Not independently derived | Not reconstructed | Depends on C1/C2 | N/A | Excluded |
| C7 468 Bernstein coefficients | **UNVERIFIED** | Enclosure theorem conditional on polynomial | No coefficients regenerated | Depends on C1/C6 | N/A | Excluded |
| C8 e-factor | **CONDITIONAL** | Conditional expectation proof derived | Formula boundary only | Actual stream law unverified | Requires conditional mean bound each step | Excluded |
| C9 recurrence/prior/threshold | **CONDITIONAL** | Recurrence, prior sum, `1/alpha` threshold derived | Prefix counts not rerun | Depends on C8 for model application | One fixed process only | Excluded |
| C10 fixed point | **CONDITIONAL; implementation UNVERIFIED** | Down-rounding argument derived | 199-bit reported maximum not reproduced | N/A | Not a guarantee alone | Excluded |
| C11 delay | **CONDITIONAL** | Freedman form derived | Numerical rows not recalculated | Exact categorical assumptions only | Sustained conditional drift/range required | Excluded |
| C12 controller | **CONDITIONAL; completeness UNVERIFIED** | Text-level invariants | No state-space checker | Implementation conformance unverified | No repeated-switch guarantee | Excluded |

## C5 correction

The amendment’s “rank-2” entry does not identify its parameter subset, point, scales, Jacobian or cutoff. Pinned NS-5A evidence specifies a different, explicit result: 45 means (40 detector marginals plus 5 pair-cofire means), three free parameters `(p_b,p_m,p_g)`, nominal `(.010,.003,.003)`, scales `(.008,.004,.001)`, whitened/scaled `45×3` central finite differences, relative rank cutoff `1e-8`, singular values `.2977118122,.1699153002,.1072531200`, and reported numerical rank **3**. A separate approximate-DEM result also reports rank 3 for a different feature law. A two-parameter restriction is a distinct result and remains unspecified/unverified; do not conflate it with the three-parameter map.

## Dependency rule

C1 stop blocks source-dependent C2 application, C3, C5, C6 and C7. It does not erase the abstract C2 identity or block the assumption-level analyses C4 and C8–C12. No aggregate PASS is assigned. Model fidelity, statistical validity, and decoder utility remain separate axes.
