# Q-SHIFT Phase 3A deterministic implementation validation

## Execution record

Reviewed base: `abcafd6f36023ae5016ccf2e7c69a674e608351d`; branch `qshift-advanced-research`. Template generation command:

```text
python outputs/qshift_advanced_research_v3a/generate_templates.py
```

It completed in **26.664 seconds** with Stim **1.16.0**, producing a `[21,11,45]` exact-categorical bank and a separate `[21,11,45]` approximate-DEM bank. Template-bank SHA-256: `be99f5f888d8e0523b6e1a0c1e054b28ccee0fcda5285c73d8ec2fa8a1c0864d`. The generator checked save/load round-trip equality. The five burst masks reproduced `(D8,D10)`, `(D16,D18)`, `(D24,D26)`, `(D32,D34)`, `(D36,D38)`.

Deterministic test command:

```text
python -m unittest discover -s outputs/qshift_advanced_research_v3a/tests -v
```

Result: **13 tests passed** in **3.935 seconds**. Coverage includes pair feature indexing, A/B population recovery, mismatch bias, boundaries, exact tie handling, malformed inputs, serialization, exact-versus-DEM provenance, fixed-gate sensitivity evidence, study-config arithmetic, deterministic paired-root analysis, and Phase 2C source-hash preservation. `py_compile` passed for estimator, generator, study runner, analysis script and tests. Both study/analysis CLI help paths were checked; neither generates histories. The runner's fail-closed authorization check is unit-tested before seed-manifest access.

## Deterministic population checks

Using the fixed exact-categorical bank, B recovered nominal `(.008,.003)`, mismatch `(.008,.006)`, and corners `(0,0)` and `(.020,.010)` exactly on the declared fitting grid. Source-faithful A returned `.008` nominal and `.01091` burst probability under actual measurement p `.006`, with measurement assumed `.003`. This is population-template objective recovery, not finite-history accuracy.

With DEM templates, B separately recovered the same nominal/mismatch pairs; the family provenance and means differ from exact categorical. The bank records fixed gate p `.003`. Existing deterministic gate-stress results show that with actual gate p `.002/.004`, fixed-gate joint fitting returns approximately `(.0083,.0004)` / `(.0077,.0056)` for `(p_b,p_m)`. Gate p is documented as an assumption and is not an estimator parameter.

## Preservation, sampling and limits

The source-preservation test recomputed hashes for the Phase 2C files listed in the Phase 2C-R1 manifest and passed. Git change review will verify that this commit contains only this new versioned directory. No Stim sampler was called, no stochastic detector history or seed manifest was created, and no decoder, logical observable, Stage 5 data, V2.4 file or PR #1 was accessed or modified.

The future study executor was not invoked. It requires both a new authorization record matching the final protocol hash and a pre-created development-only seed manifest. Analytical templates condition the proposed study on a fixed model bank; empirical template-calibration uncertainty is not included. No finite-history accuracy, gate robustness outside the listed stress points, resource performance, decoder benefit, LER improvement, or 99.99% suppression claim is established.
