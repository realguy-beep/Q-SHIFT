# Stage 4C Interpretation

## Main finding

The detector-only CNN did **not** improve adaptive PyMatching over the Stage 4B statistical profile estimator on fresh paired development data. It made 482 errors on 87,500 shots versus 478 for the profile estimator. The equal-weight nonzero-condition paired difference was +0.00004286 LER (CNN worse), root-bootstrap 95% CI [0, +0.00012857], and the two-sided root sign-flip p-value was 1.0. The result fails every primary CNN-advantage criterion; the CNN recommendation is **DROP**.

The CNN was also less accurate at estimating burst probability: nonzero-p MAE 0.0008653 (95% root-bootstrap CI 0.0006830–0.0010424), versus 0.0006643 for the profile estimator and 0.0005454 for Ridge. It overestimated the zero-burst setting and under-estimated the 0.004 and 0.008 conditions. At the three higher evaluation probabilities, CNN and profile-assisted matchers made identical predictions on every paired shot. Their only decision changes occurred in the zero and 0.004 conditions, where CNN's corrections were net harmful by four errors.

## Other decoder results

On the same fresh evaluation arrays, fixed nominal PyMatching made 545 errors; the refit Stage 4B profile method made 478; Ridge made 477; and the privileged true-p reference made 477. The Ridge-versus-profile equal-weight effect was only −0.00001143 LER and Holm-adjusted sign-flip p=0.4989. The single-error Ridge/oracle differences are not evidence that either decoder is superior. CNN versus fixed nominal had fewer errors, but the profile estimator and Ridge did at least as well; this does not establish a CNN-specific benefit.

The repeat of profile-assisted decoding's lower error count than fixed nominal is consistent with Stage 4B's development result on new samples. It remains a development comparison and does not establish generalization to hardware, other burst locations, code sizes, or real nonstationary noise.

## Limitations

- Seven independent evaluation roots per condition provide limited root-level precision.
- One frozen CNN architecture and one initialization/training allocation were evaluated; results do not prove all neural estimators are ineffective.
- Validation used p={0.005,0.015}; evaluation conditions were p={0,0.004,0.008,0.012,0.016}. No out-of-range generalization was tested.
- The simulator uses a synthetic independent-per-round pair burst, not measured hardware noise.
- Stim's categorical two-qubit DEM conversion still uses `approximate_disjoint_errors=True`.
- The true-probability decoder is a privileged reference.
- No independent-test samples were allocated or accessed.

The simpler detector-profile estimator remains the preferred adaptive parameter estimator. An independent confirmation would be a separate, frozen study; it should not be inferred from this exploratory result.
