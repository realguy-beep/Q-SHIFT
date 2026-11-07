# Existing-bank oracle headroom

## What the oracle means

For each saved shot, every archived decoder prediction is compared with the saved logical-observable label. A hindsight oracle chooses whichever candidate was correct on that same shot, when possible. This is the empirical minimum error among the stored predictions. It uses information unavailable at inference—specifically the true logical result—and is optimistic because it is evaluated on the same outcomes used to choose the candidate. It is not an estimate of a deployable policy, not a theoretical bound on unrepresented decoders, and not evidence that detectors can identify the correct candidate.

The independent scripts also record pairwise prediction disagreement, errors made only by decoder i, only by decoder j, and jointly wrong shots. For binary outputs, a pair with complementary errors has a lower per-shot oracle risk than either fixed choice. `PAIRWISE_COMPLEMENTARITY.csv` contains these counts by study, condition, root, and decoder pair. Exact equality on finite samples is not structural equivalence.

## Descriptive oracle gaps

| Bank / conditions | Strongest eligible fixed LER | Same-shot hindsight LER | Absolute gap | Relative reduction vs fixed | Interpretation |
|---|---:|---:|---:|---:|---|
| Phase 2A, 9 models, 3 regimes | 0.0069867 | 0.0049583 | 0.0020283 | 29.03% | Calibration chose model 1 globally and in each regime; hindsight combines predictions after observing labels. |
| Phase 2B, 3 models, 6 basis/composition cells | 0.0046100 | 0.0035425 | 0.0010675 | 23.16% | Basis-specific fixed models tie the regime-informed calibration choice; shotwise oracle uses labels. |
| Phase 4A, 3 comparator predictions, 3 regimes | 0.0070039 | 0.0059961 | 0.0010078 | 14.39% | The positive specialist result is against nominal fixed; the per-shot oracle is over the three saved predictions. |
| Phase 4B, 3 comparator predictions, measurement-heavy | 0.0019417 | 0.0015150 | 0.0004267 | 21.97% | Static calibration versus nominal; the oracle is an upper-limit diagnostic, not a policy. |
| Phase 4C Stage 2, 5 comparator predictions, 3 regimes | 0.0068928 | 0.0054706 | 0.0014222 | 20.63% | Uses the strongest pooled fixed as comparator; the per-shot minimum is label-informed and uses only the five stored predictions. |
| Correlation pilot, 4 fixed arms, 6 strata | 0.0049056 | 0.0032000 | 0.0017056 | 34.77% | Candidate set includes regime-informed arms and both correlation settings; not adaptive headroom. |
| Multi-distance headroom, 12 banks | 12 bank-specific fixed comparisons | Bank-specific shotwise oracles | 0.0001200–0.0008667 | Bank-specific | 180 independent evaluation roots total, only 5 roots per bank/regime. The frozen specialization gate failed. |

The bootstrap intervals stored beside these estimates resample roots within each condition, but remain descriptive intervals around a same-label hindsight quantity. They must not be reported as uncertainty for a causal detector-only selector.

## The key gate: calibration-selected specialization

The headroom study covered 12 banks (native and Pauli-biased noise; distances 3, 5, 7; X and Z memory) and 36 bank-by-regime evaluation cells. Calibration selections were independently recomputed from saved calibration arrays and matched all 12 saved pooled/per-regime selections. A specialist differed from the pooled choice in 14 cells; its independent-evaluation LER was lower in 7, higher in 6, and equal in 1. Of 702 pairwise candidate contrasts, 95 produced identical predictions on the finite evaluation arrays. Only one single regime cell met all per-cell numeric thresholds; no qualifying pair of regime specialists replicated across two distances. The preregistered headroom gate is NO-GO.

The 95 finite-sample prediction-identical pairs do not share identical saved DEM/graph signatures. Thus they are finite-sample decision coincidences, not proof of decoder-function equivalence. Conversely, distinct graph/weight structures do not imply meaningful logical utility: observed prediction differences are sparse and often do not favor the selected specialist.

## Reproducible boundaries

- All listed oracle counts are recomputed from paired predictions and labels wherever the arrays are saved.
- Phase 4C Stage 2’s 60 test checkpoints have independent prior decoder re-decoding verification; this audit independently recounts stored prediction/observable residuals. Its calibration fit cannot be rebuilt because calibration arrays are absent.
- Phase 3B predictions are not saved in raw bundles, so no shot-level oracle is claimed there.
- No oracle is reported for the summary-only Phase 5D/5E dynamic records.

