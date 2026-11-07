# Stage 5 Endpoint B — statistical design validation

**Classification:** Prespecified synthetic root-effect design simulation; no quantum shots were generated here. No Stage 5 evaluation samples or sealed historical test data were accessed. The simulation protocol and source were hashed in `DESIGN_VALIDATION_FREEZE.json` before the run.

## Design evaluated

Endpoint B is the one-sided mean test \(H_0:\Delta\ge -0.0002\) vs \(H_1:\Delta<-0.0002\), where \(\Delta\) is the equally weighted mean of four nonzero-condition, root-level paired differences (`adaptive LER − nominal fixed LER`). The null boundary has alpha=.05 rejection probability; “power at the boundary” is not a useful target. The proposed allocation has n=256 independent roots in each of five conditions, with 2,000 calibration plus 2,500 paired evaluation shots/root: 1,280 roots, 2.56M calibration shots, 3.20M evaluation shots, 5.76M total.

For the primary mean, the proposed review v1 used Welch–Satterthwaite inference over the four independently sampled condition means. We simulated independent root-level paired effects with condition-specific SDs taken as the larger Stage 4/4C development SD (each source cell had only seven roots), then applied root-SD multipliers 1, 1.5, and 2. Stress distributions were Student-t(5), standardized lognormal, and 65%-zero-inflated normal. A null with nonzero condition-specific offsets summing to zero tested the equal-weight contrast. Each Welch cell used 10,000 Monte Carlo experiments. Wilson 95% intervals below describe Monte Carlo error only; they do not cover uncertainty in the seven-root variance estimates.

## Welch operating characteristics

At the B boundary \(\Delta=-0.0002\), rejection is type-I error; central coverage is the ordinary two-sided 95% Welch interval coverage. Power columns test true \(\Delta=-0.0003\) and −0.0004.

| Root-effect scenario | Type-I at boundary (95% MC interval) | Central 95% CI coverage (95% MC interval) | Power at −0.0003 | Power at −0.0004 |
|---|---:|---:|---:|---:|
| Normal, SD ×1.0 | 5.11% [4.70, 5.56] | 94.49% [94.03, 94.92] | 80.52% | 99.94% |
| Normal, SD ×1.5 | 5.60% [5.17, 6.07] | 94.75% [94.30, 95.17] | 50.92% | 95.43% |
| Normal, SD ×2.0 | 5.15% [4.73, 5.60] | 95.34% [94.91, 95.74] | 33.97% | 80.36% |
| Student-t(5), SD ×1.5 | 4.59% [4.20, 5.02] | 95.17% [94.73, 95.57] | 51.19% | 94.89% |
| Right-skew lognormal, SD ×1.5 | **7.57% [7.07, 8.10]** | **94.32% [93.85, 94.76]** | 53.46% | 91.64% |
| 65% zero-inflated normal, SD ×1.5 | 4.97% [4.56, 5.41] | 94.97% [94.52, 95.38] | 49.88% | 95.42% |
| Normal, SD ×1.5, balanced stratum offsets | 4.86% [4.46, 5.30] | 95.14% [94.70, 95.54] | 51.20% | 95.10% |

The equal-stratum Welch test is close to nominal in most scenarios, but the right-skew stress has an elevated false-positive rate whose Monte Carlo interval excludes 5%; its one-sided upper-bound coverage is 92.43% [91.90, 92.93]. This is a material failure for the proposed primary claim. The normal ×1.5 case also shows some size/coverage drift. The result is not cured by more roots alone unless inference is also validated under plausible skew.

Multiplicity: the primary threshold test is one prespecified test at one-sided alpha=.05; the four nonzero-condition secondary tests remain a single Holm family. The p=0 no-harm condition is a separately required safety conjunct, not a separate superiority claim. The powers in the table are **primary-test power only**; they do not estimate the probability of passing the entire conjunction (including all four condition-direction requirements, the p=0 gate, and any Holm-adjusted condition claims). The old Endpoint A zero-null test must not be substituted after a failed B test.

## Root-stratified bootstrap-t sensitivity

For three null scenarios, 1,000 outer experiments each used 399 within-stratum root bootstrap resamples. These counts are adequate for a feasibility warning, not precise coverage certification.

| Scenario | Type-I (95% MC interval) | Central 95% coverage (95% MC interval) |
|---|---:|---:|
| Normal, SD ×1.5 | 4.60% [3.47, 6.08] | 95.00% [93.47, 96.19] |
| Right-skew lognormal, SD ×1.5 | 5.20% [3.99, 6.76] | 94.30% [92.69, 95.57] |
| 65% zero-inflated normal, SD ×1.5 | 4.40% [3.29, 5.86] | 95.40% [93.92, 96.53] |

All bootstrap-t Monte Carlo intervals include nominal 5%/95%, but are wide. The current evidence does **not** establish bootstrap-t coverage, and the review v1 “Welch primary plus bootstrap sensitivity” rule is insufficiently precise: a post hoc judgment that results “do not materially conflict” cannot be the success rule. A new prospective design must select and calibrate one inferential procedure, define exactly how the sensitivity interval affects the claim, and rerun operating-characteristic simulations before any Stage 5 sampling.

## Power and between-root heterogeneity

At n=256, the simulation gives about 80.5% power at true \(\Delta=-0.0003\) under nominal SD, but only 50.9% under the 1.5× SD normal scenario and 34.0% under 2× SD. At −0.0004 the corresponding normal powers are 99.9%, 95.4%, and 80.4%. Thus 256 roots are an 80% design for a 0.0001 gap beyond the margin only under the nominal seven-root SD estimates; they are not robust to moderate root heterogeneity.

The analytic planning sensitivity requires about 256 roots/stratum for 80% power at a .0001 gap beyond −.0002 under nominal SD, 575 roots under 1.5× SD, and 1,023 under 2× SD. Across five strata and 4,500 shots/root, those correspond to 5.76M, 12.94M, and 23.02M shots. For 90% power, nominal SD requires 354 roots (7.97M), while 1.5× SD requires 797 (17.93M). The existing 2.5M Stage 5 cap permits at most 111 roots/stratum and cannot meet the modest-effect target. If the target alternative is instead −0.0004, n=256 appears ample under the tested distributions, but that assumes an effect twice the practical margin and should not be selected just to fit resources.

### Separate p=0 safety check

The no-harm gate tests an upper limit against +0.0002, separate from the nonzero-condition estimand. Using the larger observed p=0 development SD, 0.0001512 from seven Stage 4 roots (Stage 4C had zero SD across seven roots), normal-root simulations at n=256 had 5.09–5.27% rejection at the +0.0002 boundary across SD multipliers 1–1.5 and essentially 100% pass rate at true effect 0. At 2× SD, the boundary rejection rate was 5.14%. A 65%-zero-inflated mixture at the boundary was mathematically incompatible with the specified mean/SD for multipliers 1 and 1.5, so those cases were recorded as not simulated; at 2× SD it produced 5.80% rejection [5.36, 6.28]. This is a stress-model warning, not an estimate of actual p=0 behavior.

## Statistical decision

**NO-GO for Stage 5 sampling under this candidate.** The nominal n=256 power story depends on unverified seven-root variance estimates, the proposed Welch test exceeded the .05 type-I level under the prespecified skew stress, and the bootstrap-t sensitivity has too few outer simulations to establish coverage. Do not run Stage 5 with this candidate amendment. Before re-review, prospectively select an inference method with controlled operating characteristics across skew, ties/zero inflation, and 1.5×/2× heterogeneity; define any combined Welch/bootstrap rule mathematically rather than subjectively; accept a target effect beyond the margin; and obtain a resource ceiling consistent with the resulting root count.

Full per-scenario values and Monte Carlo intervals: `DESIGN_SIMULATION_RESULTS.json`. Configuration, RNG stream inventory, and pre-run hashes: `DESIGN_SIMULATION_CONFIG.json`, `VALIDATION_SEED_INVENTORY.json`, and `DESIGN_VALIDATION_FREEZE.json`.

### Reproducibility metadata caveat

The simulation source uses one PCG64 stream per Welch scenario and consumes the four effect cases sequentially. A row-level `seed` field in the saved JSON is an offset label, not the seed of an independently initialized stream. Reproduction is defined by the scenario seed and fixed effect order in `SIMULATION_SEED_PROVENANCE_NOTE.md`. The output and frozen source were preserved unchanged; future validation versions should use explicit scenario-seed and effect-order fields.
