# V2 scientific fairness and leakage review

**State:** source/design review only. V2 has produced no samples and remains unauthorized to sample.

## Primary comparison and five arms

The primary scientific contrast is the equal-weight mean across the four nonzero burst conditions of paired root-level `adaptive_profile - pooled_detector_static` LER. Pooled-fixed PyMatching is the strong conventional comparator. The safety-constrained static decoder remains a separate arm and retains its p=0 selection/validation no-harm gate. The arms remain nominal fixed, pooled detector-only static, safety-constrained static, per-root adaptive, and privileged true-p (reference only).

The privileged reference receives the generating probability and is not deployable. It is not used for policy selection or the primary estimand. Every arm for a root receives the same detector matrix and observable vector. Paired differences therefore use shot-identical labels and syndromes; only decoder model/selection differs.

## Calibration and label access

- Profile features are fit from three independent template batches with known template-generation probabilities (p=0, .01, .02). These probabilities identify the calibration templates only.
- Pooled-static p estimation receives one concatenated matrix of final calibration detector rows; its estimator API accepts arrays, not `(p, detectors)` tuples. The per-root adaptive estimator receives that root's separate 2,000-shot detector-only calibration matrix.
- Neither deployable estimator receives observable labels, simulator event flags, generating condition labels, or evaluation-root information. The root's detector calibration completes before its evaluation stream is sampled/decoded.
- Selection and validation observable labels are used only by the frozen safety-static selector. Selection chooses at most one candidate; validation only accepts that candidate or falls back to p=0. It cannot reselect.
- Final-development evaluation labels are unavailable to calibration, candidate selection, thresholding, or any model choice. They are used only for scoring after selection freezes are written.

## Resource and information differences

| Arm | Final calibration data | Additional labeled selection data | Information aggregation / compute |
|---|---:|---:|---|
| Pooled detector-static | 1.2M detector shots + shared 60k templates | none | Concatenates all final calibration rows into one estimate/model. |
| Per-root detector-adaptive | 1.2M total detector shots + shared 60k templates | none | Each estimate sees only 2,000 rows from its current root; up to 600 root-specific estimates and model builds. |
| Safety-constrained static | Same selection/validation archives used for comparator scoring | 450k selection + 450k validation shots with observables | Searches nine candidate models, then validates one; it receives 900k additional labeled shots and is not equal-information to deployable calibration arms. |
| Nominal fixed | no experiment-specific calibration | none | Fixed p=0 decoder. |
| Privileged true-p | hidden generating p | none | Diagnostic upper-reference information; not deployable. |

The pooled and adaptive arms have equal *total* final calibration shots and shared templates, but not equal local estimator sample size, information pooling, model-rebuild count, or runtime. The selector's extra 900k labels are disclosed rather than described as equal-resource. Report calibration, estimator, decoder construction, and inference time separately if later executed.

## Seed separation and evidence boundaries

The V2 inventory assigns different seeds to templates, selection calibration/scoring, validation calibration/scoring, final calibration, evaluation, bootstrap RNG, and benchmark-only streams. The collision audit uses only named seed inventories/seed manifests and the exact historical metadata allowlist recorded by the prior Stage 5 seed audit. It does not open shot archives or outcome arrays. All files actually checked and hashes are recorded in `seed_inventory_v2_r2.json`. The earlier no-sample candidate inventory is preserved and is not treated as historical RNG usage.

The screening is complete for the recoverable named metadata sources, not for undocumented historical RNG use. This limitation is explicit. No V2 samples are generated. The Stage 5 evaluation outcomes remain sealed and untouched.

## Statistical interpretation

V2 is development-only. Root clusters, not individual shots, are the resampling units. The primary interval resamples roots within each fixed nonzero condition and gives the four conditions equal weight. The 100,000-resample 95% percentile interval is descriptive; there are no confirmatory p-values or multiplicity claims. Report the `0.0002` effect-size benchmark separately and do not call an effect smaller than it practically meaningful. Report the p=0 safety gate and all five arms without selecting from final-evaluation labels.

## Remaining fairness limitations

The finite five-condition synthetic circuit does not establish general noise-family performance. The adaptive arm's per-root estimate and repeated model reconstruction may be more costly than pooled-fixed even at the same total calibration-shot count. The safety-static arm has extra supervised selection data. A later study must report these differences, not normalize them away, and must include paired root-level uncertainty and an independent archive/prediction audit before drawing conclusions.
