# Bounded-mean e-process feasibility

**Classification:** deterministic model-feasibility evidence. No e-detector, alarm, data sequence, decoder action, or performance evaluation was run.

## Literature connection

Shin, Ramdas and Rinaldo, *E-detectors: A Nonparametric Framework for Sequential Change Detection*, New England Journal of Statistics in Data Science 2(2), 229–260 (2024), [DOI](https://doi.org/10.51387/23-NEJSDS51), [full text](https://nejsds.nestat.org/journal/NEJSDS/article/59/text), construct sequential detectors from baseline increments whose conditional expectation is at most one for every law in a declared pre-change class. For a statistic $X_t\in[0,1]$ with a uniform conditional null mean bound $E[X_t\mid\mathcal F_{t-1}]\leq m$, their bounded-variable construction permits

$$
L_t=1+\lambda(X_t/m-1),\qquad 0\leq\lambda\leq1.
$$

An e-detector built from valid increments admits nonasymptotic average-run-length (ARL) control at the paper's threshold. ARL control is distinct from fixed-horizon false-alarm probability or a bound on repeated false decoder switches.

## Statistic and exact-circuit continuous certificate

Use the detector-only per-shot statistic

$$
X_t=\frac{1}{5}\sum_{j=1}^{5}D_{a_j,t}D_{b_j,t}\in[0,1],
$$

where the five pairs are the documented burst detector supports. Under the exact categorical circuit with gate $p_g=.003$, null burst probability $p_b\in[0,.002]$, and measurement probability $p_m\in[.001,.005]$, the exact population mean $g(p_b,p_m)=E[X]$ is a degree-8 polynomial in $u=1-2p_m$ for each fixed $p_b$.

`measurement_nuisance_mean_certificate.py` forms this polynomial from categorical parity-character factors using exact `Fraction` arithmetic for the fixed channel probabilities. The derivative's seven Bernstein coefficients on $u\in[.99,.998]$ are all negative (range `[-0.0613732871, -0.0392455561]`). Therefore $g$ is increasing in $p_m$, and the continuous null supremum is attained at $p_m=.005$:

$$
m_0=\sup_{p_b\in[0,.002],\,p_m\in[.001,.005]}g(p_b,p_m)=0.00269469102575917.
$$

Independent feature-expectation checks at $p_m=.001,.003,.005$ differ by at most $9.81\times10^{-17$.

The wider rectangle is handled by `exact_burst_measurement_rectangle_certificate.py`. The five burst error supports match the five disjoint detector pairs. Each pair-cofire mean is affine in the common independent burst probability because only its corresponding burst site flips both bits in that pair. At $p_b=.002,.010,.018$, the derivative with respect to $p_m$ is certified positive throughout the measurement interval by exact rational Bernstein signs. The Bernstein coefficients of both mean differences $g(.010,p_m)-g(.002,p_m)$ and $g(.018,p_m)-g(.010,p_m)$ are strictly positive throughout the interval. Affinity in $p_b$ therefore proves the null mean increases over $[0,.002]$ and the alternative mean increases over $[.010,.018]$. The $p_b=0$ endpoint is the analytic limit of the same law even though the circuit builder removes the zero-probability instruction. Consequently, over the exact categorical circuit alternative rectangle $p_b\in[.010,.018]$, $p_m\in[.001,.005]$:

$$
\inf E[X]=g(.010,.001)=0.00997074427026786,
\qquad \inf E[X]-m_0=0.00727605324450869.
$$

The maximum derivative Bernstein coefficient ranges and cross-validation results are recorded in `EXACT_BURST_MEASUREMENT_RECTANGLE_CERTIFICATE.json`. The polynomial fits the original feature-moment calculation at three measurement-noise probes within $10^{-16$.

This upgrades the exact-circuit null conditional-mean envelope from a grid result to a continuous certificate over the declared burst and measurement intervals. If $p_m$ and $p_b$ vary predictably from shot to shot within those intervals while gate noise remains fixed, the same per-shot envelope applies conditionally. A conservative implementation value could be the certified $m_0$ plus a declared numerical safety margin; the certificate itself is a population calculation, not an implemented controller.

## Approximate DEM remains separate

| Model | Null $p_b=.002$: maximum | Alternative $p_b\in[.010,.018]$: minimum | Gap |
|---|---:|---:|---:|
| Exact categorical circuit, continuous certificate | 0.0026946910 over $p_b\in[0,.002]$, maximum at $p_b=.002,p_m=.005$ | 0.0099707443 at $p_b=.010,p_m=.001$ | 0.0072760532 |
| Approximate DEM, 101-point $p_m$ grid | 0.0026936574 at $p_m=.005$ | 0.0099703842 at $p_b=.010,p_m=.001$ | 0.0072767268 |

The DEM has not received a continuous interval certificate. The DEM figures are exact only for the resulting approximate independent-event model, not the original circuit law. Reproduction sources/results are `bounded_pair_statistic_mean_grid.py` and `BOUNDED_PAIR_STATISTIC_MEAN_GRID.json`.

## Population log-increment calculations

`bounded_eincrement_growth_audit.py` aggregates the exact ten-detector joint law into the six possible values of $X$ and evaluates expected log increments. For the exact circuit it uses $m=m_0+10^{-10}$ from the continuous certificate; for the DEM it uses the finite-grid maximum plus the same margin. A 10,000-point $λ$ grid gives exact-circuit expected log increments of `0.028721–0.030276` nats/shot at $p_b=.010$ and `0.089886–0.090705` at $p_b=.018` across $p_m=.001,.003,.005`; DEM rates are `0.028733–0.030286` and `0.089914–0.090730`. Lambda optima are numerical grid maxima, not exact optimizers.

The certified exact-circuit alternative mean also gives a conservative positive-drift statement for one fixed small $\lambda=10^{-5}$. With $m=m_0+10^{-10}$, $R=1/m-1=370.1000$ bounds $|X/m-1|$, so $\lambda R=.003701<.5$. Using $\log(1+y)\ge y-y^2$ for $|y|\le .5$ gives

$$
E[\log L_t]\ge \lambda\left(\frac{0.00997074427026786}{m}-1\right)-\lambda^2R^2
=1.3304\times10^{-5}\text{ nats/shot}.
$$

This is a deterministic lower bound on the expected log increment over the certified alternative rectangle, not a detection-delay or finite-horizon false-alarm bound. Full grid results are in `BOUNDED_EINCREMENT_GROWTH_AUDIT.json`.

## Limits and remaining design decisions

- The continuous certificate fixes gate $p_g=.003$ and bounds null burst $p_b\in[0,.002]$. It excludes gate-noise drift, correlated readout, calibration uncertainty, burst probability above `.002` under the null, and other physical mechanisms.
- A first attempt to include the $p_b=0$ endpoint in null reweighting failed because the circuit builder omits zero-probability burst sites, changing the template site count. That implementation failure is preserved in `BOUNDED_PAIR_STATISTIC_MEAN_GRID.json`; the later analytic affine extension covers the $p_b=0$ limiting law without reweighting a zero-probability circuit.
- A valid alarm detects excess pair-cofire mean only. It neither identifies physical cause nor estimates the burst rate, chooses a useful matching graph, bounds decoder utility loss, or demonstrates lower logical error.
- The e-detector literature's ARL guarantee is not automatically a fixed-horizon false-switch guarantee. Choose between ARL, horizon-wise false-alarm probability, and expected false graph-switch count; specify reset and repeated-switch handling.
- No sequential process, threshold, false-alarm rate, delay, or action policy has been implemented or validated. Any future evaluation requires separate authorization.



## Information retained by the six-level cofire count

A deterministic data-processing comparison aggregates the ten selected detector bits to the count $C=5X\in\{0,1,2,3,4,5\}$. Across the three burst steps and $p_m=.001,.003,.005$, the compressed count's simple-IID KL retains 90.33%–99.26% of the full ten-bit KL across the exact categorical circuit and approximate DEM. At nominal $p_m=.003$, exact-circuit retention for `.002→.010`, `.010→.018`, and `.002→.018` is 93.62%, 98.43%, and 94.48%, respectively. The six-state count law is therefore a potentially efficient detector-only input under these model comparisons.

This is the KL of the full six-category count observation, not the expected-log performance of the bounded-mean betting increment. Data processing guarantees the count cannot have more KL than the full 1,024-state observation; the saved audit checks that inequality directly. The result assumes identical measurement p before and after and does not compare false alarms, delay, decoder actions, or logical outcomes. A richer safe process over the six count categories could be investigated, but would need its own null-valid e-value construction and certified category/tail bounds. Source/result: `cofire_count_information_audit.py`, `COFIRE_COUNT_INFORMATION_AUDIT.json`.

## A concrete sequential construction remains possible

Under the exact certified null, choose $m>m_0$ and any fixed $\lambda\in[0,1]$, then use $L_t=1+\lambda(X_t/m-1)$. For each possible change start $j$, form $\Lambda_t^{(j)}=\prod_{i=j}^{t}L_i$ (and set it to 1 before j). A fixed mixture over several lambdas remains a valid $e_j$-process; the Shiryaev–Roberts e-detector $M_t=\sum_{j=1}^{t}\Lambda_t^{(j)}$ then has the paper's nonasymptotic ARL guarantee at threshold $1/\alpha$. This is the natural unweighted-start candidate for a continuing monitor, but ARL may not match a controller's finite-horizon false-switch requirement.
For one finite deployment horizon or a family-wise “ever alarm” requirement, use predeclared start weights whose total is at most one; the cited paper shows the weighted construction yields a false-alarm probability bound, with a delay cost that grows with the start-time weight. A perpetual controller that resets after graph changes would need explicit alpha spending across resets/switches. These are different operational objectives and remain owner decisions. No recursion was run on observations and no threshold was selected.



## Independent old/new measurement-nuisance stress on the cofire count

`cofire_count_dense_nuisance_audit.py` extends the earlier same-$p_m$ comparison to independent old and new measurement probabilities on identical 101 by 101 grids over `[.001,.005]`. For every burst transition, it computes exact circuit and approximate-DEM ten-bit laws, compresses each to the six-category count $C$, and compares directed $D_{KL}(P_{new}\|P_{old})$. Maximum normalization error is `1.80e-14`; the maximum observed coarsened-minus-full KL is zero, satisfying data processing.

The independently minimized grid KLs (exact circuit; DEM differs by at most `2.8e-5` nats/shot) are: `.002→.010`, full `0.0336590`, count `0.0289400`; `.010→.018`, full `0.0117140`, count `0.0111205`; `.002→.018`, full `0.0990910`, count `0.0899130`. These minima do not generally occur at the same old/new measurement pair. Therefore their ratio is not an information-retention fraction at a common nuisance setting.

When old and new measurement probabilities are held to the same pair for the full and compressed comparison, the worst count/full KL ratio over the grid is `55.97%` for `.002→.010` (old/new `p_m=.005/.001`), `34.68%` for `.010→.018` (`.001/.005`), and `76.35%` for `.002→.018` (`.005/.001`). At the measurement pair minimizing the full-law KL, corresponding count/full ratios are `90.23%`, `97.24%`, and `91.56%`. Exact-circuit and approximate-DEM ratios are numerically very close here.

This shows the count retains less relative information at some severe, oppositely directed measurement changes than under the previous common-measurement comparison. It does not show that the count is unidentifiable: all grid-minimum count KLs remain positive for these specified burst transitions. Nor is the grid a continuous nuisance infimum, a sequential operating characteristic, or evidence about finite-history test power. The statistic-specific bounded-mean e-process has a separate exact-circuit conditional-mean certificate only for the previously declared bounded nuisance rectangle and fixed gate model; this KL audit does not extend or replace that certificate. Reproduction: `cofire_count_dense_nuisance_audit.py`; data: `COFIRE_COUNT_DENSE_NUISANCE_AUDIT.json`.

## Checkpoint 110 — exact continuous category-wise e-factor construction

A second, richer construction uses the six-category count $C\in\{0,\ldots,5\}$ of the five within-pair detector cofires. `cofire_category_continuous_envelope.py` derives each $P(C=c)$ as an exact rational bivariate polynomial in $v=1-2p_b$ and $u=1-2p_m$. It obtains the joint cofire-bit moments from parity characters of the independent categorical circuit, then applies Bernoulli subset inversion and aggregates by count. The polynomial law normalizes identically. Its degrees are 5 in $v$ and 16 in $u$.

For the exact categorical circuit with fixed gate noise $p_g=.003$, the full null rectangle $p_b\in[0,.002]$, $p_m\in[.001,.005]$ was partitioned into 4 by 4 subrectangles. Exact rational tensor-product Bernstein coefficients bound each category probability from above; the six resulting rational bounds sum to `1.011376721546938`. The upper bounds are conservative but close to the maxima on a separate floating-point 101 by 101 grid. The exact-circuit category polynomial agrees with the independently implemented ten-detector direct-XOR law at five null/alternative probe points with maximum absolute error `7.44e-15`. The few-`1e-16` apparent excesses of rounded grid values over rounded bounds are floating-point output roundoff; validity uses the exact rational upper fractions.

Given any fixed six-category proposal distribution $q$, set $L(C)=q(C)/U_C$, where $U_C$ is the certified category upper bound. For every predictable exact-model null parameter within the declared rectangle, $P(C=c\mid\mathcal F_{t-1})\le U_c$ implies $E[L(C_t)\mid\mathcal F_{t-1}]\le\sum_cq_c=1$. Thus this defines a valid one-step e-factor and products form an e-process under the stated conditional circuit model. This is an analytic construction, not an implemented detector or a stream test. Any software implementation must preserve outward-safe rounding of $U_c$ and normalization of $q$.

Two fixed proposals were screened: the exact model law at $(p_b,p_m)=(.010,.003)$ and the uniform mixture over a declared alternative grid with $p_b\in\{.010,.014,.018\}$ and five measurement values. On a separate 101-point measurement grid at each of those three burst values, minimum expected log increments were `0.0180323` and `0.0149429` nats/shot; maxima were `0.0682433` and `0.0777423`. The maximum null expected e-factor on the 101 by 101 polynomial grid was `.98916` and `.98937`, respectively. These are grid population diagnostics; only the null e-factor inequality is continuous, and it follows from the rational category bounds.

On the same alternative grid, the simpler certified mean factor with $m=m_0+10^{-10}$ and fixed $\lambda=.036$ has expected log increment `0.0287210–0.0786604` nats/shot. Thus the current category-wise proposals have lower worst-case drift and more implementation complexity; no decoder benefit is implied. Retain the scalar mean factor as the provisional simple candidate. Keep category-wise $q/U$ as a mathematically valid secondary construction if later nuisance modeling or alternative coverage justifies it. The approximate DEM has not received a continuous category envelope. Neither construction has had its threshold, finite-horizon error, repeated-switch risk, runtime, or decoder utility evaluated.

Derivation source/result: `cofire_category_continuous_envelope.py`, `COFIRE_CATEGORY_CONTINUOUS_ENVELOPE_CERTIFICATE.json`. The earlier 12 by 12 rational partition attempt was stopped before writing an artifact because it exceeded the bounded compute allowance; the optimized dyadic-factor implementation completed with 4 by 4 cells. An initial helper-interface error was corrected before the successful run.

The optional `--certify-alt-growth` switch attempts a continuous expected-log lower bound by rational log intervals plus a Bernstein enclosure. Both bounded attempts were interrupted before completion because of the large exact-rational workload (first with 4x4 expected-log subdivision and a long log series; then a single cell and shorter series). No expected-log certificate was written. The default reproduction command excludes this optional path and regenerates the completed null envelope and population-grid diagnostics. Continuous positive alternative drift therefore remains unresolved.

## Approximate-DEM transfer screen (finite grid only)

`cofire_category_dem_transfer_audit.py` applied the exact-circuit rational category bounds to approximate-DEM category laws on five null burst values (`.0001,.0005,.001,.0015,.002`) by 101 measurement values, and three alternative burst values (`.010,.014,.018`) by the same measurement grid. No category probability exceeded its exact-circuit upper envelope on these grid points. The maximum DEM null expected e-factor values were `.9891505` for the reference proposal and `.9893495` for the mixture; alternative expected-log ranges were `.0180300–.0682411` and `.0149400–.0777395` nats/shot. The largest category-law normalization error was `9.10e-15`.

This close agreement is useful model-approximation evidence but is only a finite DEM grid. It does not prove the exact circuit envelope dominates DEM laws continuously, and it cannot establish any validity under physical model error. The exact-circuit theorem remains the only continuous e-factor result. Source/result: `cofire_category_dem_transfer_audit.py`, `COFIRE_CATEGORY_DEM_TRANSFER_AUDIT.json`.

## Model-grid proposal optimization screen

`cofire_category_proposal_minimax.py` selects a fixed rational six-category proposal by numerically maximizing a smooth soft-min over the 303 model-generated alternatives (`p_b=.010,.014,.018` by 101 measurement values). The resulting $q$ has a measured minimum grid expected-log increment of `0.0180357` nats/shot; a denser 1001-point measurement sensitivity grid gives the same minimum, so the measurement discretization appears stable at the recorded precision for these three burst values. The reference proposal gave `0.0180323`, while the fixed-λ scalar mean factor gave `0.0287210` on the same alternative grid.

The soft-min approximation gap is bounded by `log(303)/2500 = 0.0022855` nats/shot. The SLSQP solve converged numerically, but this is not an independently certified global optimizer result; the alternative region is still represented by three burst values and the continuous positive-drift enclosure did not complete. The gain over the reference proposal is negligible and the scalar mean factor has materially higher tested population drift. Do not add model-grid q tuning to the preferred architecture absent a policy-specific reason. Any selected normalized q still yields the exact-model null e-factor with the certified rational category bounds.

Two SLSQP formulations failed (`inequality constraints incompatible`), first with all 303 inequalities and then with a cutting-plane subset. The smooth soft-min formulation succeeded. Failures are preserved in the research log; no failed optimizer generated an artifact. Source/result: `cofire_category_proposal_minimax.py`, `COFIRE_CATEGORY_PROPOSAL_MINIMAX.json`.

## Bidirectional regime evidence from the certified bounded mean

The same continuous mean certificate supports a reverse one-sided test. Let $X$ be the bounded mean cofire statistic and $Y=1-X$. For an upward trigger, the null is $p_b\in[0,.002]$ and alternative $p_b\in[.010,.018]$; for a downward trigger, use $Y$ with high-regime null $p_b\in[.010,.018]$ and low-regime alternative $p_b\in[0,.002]$. Both retain $p_m\in[.001,.005]$ and gate $p_g=.003$. The certified separation in the relevant mean is `0.00727605324450869` in either direction. A fixed small $λ$ gives uniform positive lower bounds on expected log increments: `1.33040e-5` nats/shot upward at $λ=1e-5`, and `1.30480e-5` downward at $λ=.003`, using $\log(1+y)\ge y-y^2$ for $|y|\le1/2$.

This supports a two-direction **regime monitor concept**, not a generic two-sided detector. Burst probabilities in `(.002,.010)` form an explicit indifference band; measurement and gate assumptions remain as stated. A causal controller would have to maintain the current regime state, select the corresponding opposing-null process, and allocate error across resets/switches. The existing ARL/finite-horizon/false-switch objective remains undecided; no statistic was applied to a stream and no graph was switched. Derivation: `bidirectional_mean_efactor_certificate.py`, `BIDIRECTIONAL_MEAN_EFACTOR_CERTIFICATE.json`.

## Checkpoint 117 — continuous alternative log-growth certificate for the scalar mean factor

A conservative alternative to the unfinished category-log polynomial enclosure now certifies the preferred scalar factor's drift. `mean_efactor_continuous_log_growth_audit.py` obtains exact rational lower/upper bounds for each cofire-count category probability over each alternative rectangle using 4x4 tensor Bernstein partitions. It bounds each fixed rational log increment by a 20-term atanh-series interval with explicit tail and sums the least endpoint product for each category. This separately encloses all six terms of the scalar expected-log sum.

For fixed `lambda=.005`, the resulting uniform lower bounds are `0.0107107321` nats/shot for upward detection (`X`, high-burst alternative) and `0.0000367389` nats/shot for downward detection (`1-X`, low-burst alternative). Smaller tested lambda values `.001` and `.003` also have positive lower bounds. The bounds apply continuously across the full respective burst rectangles and measurement interval under the exact categorical circuit with fixed gate p=.003. They are conservative population guarantees, not realized finite-sample drift, alarm delay, ARL, or false-switch probability.

This corrects the earlier statement that continuous alternative drift remains unresolved for every candidate: it is now established for the scalar mean up/down factors. The optional exact expected-log enclosure for the richer category-wise `q/U` factor remains incomplete; no continuous alternative-growth claim is made for that method. Reproduction source/result: `mean_efactor_continuous_log_growth_audit.py`, `MEAN_EFACTOR_CONTINUOUS_LOG_GROWTH_AUDIT.json`.

## Checkpoint 118 — gate-noise mismatch breaks the fixed-gate null bounds

`gate_noise_mismatch_evalidity_audit.py` reused the deterministic fault-support map and reweighted exact categorical channels on a 3x3x3 grid: $p_g\in\{.002,.003,.004\}$, $p_m\in\{.001,.003,.005\}$, and $p_b\in\{.002,.010,.018\}$. At baseline $p_g=.003$, the previously certified boundaries agree to numerical precision. At $p_g=.004,p_m=.005,p_b=.002$, the low-regime $E[X]$ is `0.0030064726`, exceeding the fixed-gate bound `0.0026946910` by `0.0003117816`. At $p_g=.002,p_m=.001,p_b=.010$, high-regime $E[X]` is `0.0099030715`, below the required minimum `0.0099707443` by `0.0000676727`. Other tested violations include +`0.00004273` in the low regime at $p_g=.004,p_m=.003$ and -`0.00001093` in the high regime at $p_g=.002,p_m=.003`.

A single exact-model parameter point outside a conditional-mean envelope is enough to show that the corresponding e-factor validity claim does not transfer to that gate setting. The finite 27-point grid does not certify where the full gate-drift boundary lies. Therefore the scalar trigger is conditionally valid only if gate noise is fixed/known at `.003` (or a new robust envelope is proved). A future design must either declare this fixed-gate assumption enforceable, add an independently justified gate-noise telemetry guard, or derive a continuous gate-nuisance envelope. Detector-only observations have not been shown to distinguish gate drift from the target burst process. No alarms or streams were evaluated.

## Checkpoint 122 — continuous gate-robust scalar mean envelope

The fixed-gate trigger above remains invalid outside its stated gate assumption. A new deterministic extension proves a robust alternative for the scalar statistic without attributing gate changes online. `exact_three_parameter_efactor_envelope.py` builds the rational exact-categorical mean polynomial for $X$, the average of five pair-cofire indicators, using the balanced-noise source allocation $p_g/3$ for each 1Q Pauli alternative, $p_g/15$ for each 2Q Pauli alternative, $p_m$ for measurement flips, and $p_b$ for each independent burst event. It uses the existing deterministic detector-support map, and converts the resulting three-variable polynomial to tensor Bernstein coefficients.

For the full rectangles $p_b\in[0,.002]$ (null) and $[.010,.018]$ (high-burst alternative), $p_m\in[.001,.005]$, and $p_g\in[.002,.004]$, global coefficient ranges certify

- $\sup_{H_0} E[X]\le 0.003006472621297416$;
- $\inf_{H_1} E[X]\ge 0.009903071523335840$;
- a conservative mean gap of `0.006896598902038424`.

The complementary statistic $Y=1-X$ has null upper bound `0.9900969284766642` and low-burst alternative lower bound `0.9969935273787026`, with the same gap. The degrees are `(1,8,25)` in burst, measurement, and gate probability; only 468 tensor coefficients are needed per rectangle. Eight deterministic corner/interior polynomial values agree with exact-circuit feature expectations within `1.02e-16`. The balanced source channel allocations were checked at endpoints, quarter points and midpoints against Stim's floating instantiations; maximum per-alternative discrepancy was `8.68e-19`. The certificate is for the ideal rational categorical law; production implementations should retain outward-safe numerical slack.

For $Z\in[0,1]$, $f(Z)=\log(1+\lambda(Z/m_0-1))$ is concave and lies above the chord joining $Z=0,1$. Since the chord's slope is positive, the null mean upper bound $m_0$ and alternative mean lower bound yield uniform expected-log lower bounds using rational atanh-series log intervals. At $\lambda=.005$, these are `0.004718375080752108` nats/shot upward and `0.00003478894429311721` nats/shot downward on $Y$. The tested `.001` and `.003` lambdas are also strictly positive in both directions. For any predictable per-shot parameter sequence whose conditional law remains inside the relevant null rectangle, the one-step mean inequality gives a nonnegative supermartingale under the sustained null. This addresses the gate rectangle without an online gate estimator.

The value of $\lambda$ that maximizes this conservative endpoint-chord lower bound has a closed form, $\lambda^*=m_1-(1-m_1)/(1/m_0-1)$, where $m_0$ is the null mean upper bound and $m_1$ is the alternative mean lower bound. It is `0.0069173958633` upward and `0.6964100871` downward on $Y$; exact rational log intervals give chord lower bounds `0.004932537879491168` and `0.003336614487056263` nats/shot, respectively. This optimizes only the proved chord bound, not actual stopping delay, variance, numerical stability, or deployment utility. The asymmetric downward value should be treated as a theoretical candidate requiring bounded-factor implementation review.

This is a continuous population certificate, not an implemented detector, an operational delay or false-switch guarantee, or decoder utility. It assumes the declared rectangular ranges, the existing ideal independent categorical circuit and balanced gate allocation, and fresh per-shot noise conditional on the past. Gate noise outside `[.002,.004]`, correlated changes to the gate model, or other unmodeled noise invalidate the claim. Indifference-band behavior, reset/state transitions, and repeated-alarm alpha spending remain unresolved. Reproducer/result: `exact_three_parameter_efactor_envelope.py`, `EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json`.

**DEM transfer warning:** the separate 250-point approximate-DEM transfer screen found one high-alternative DEM mean below the exact-circuit lower bound by `5.9848e-8` at `p_b=.010,p_m=.001,p_g=.002`. The DEM grid itself still showed a positive low/high mean gap, but that does not validate the exact-circuit denominator or provide a continuous DEM guarantee. Keep any future exact-circuit and approximate-DEM e-factor proposals as separate, explicitly identified model arms until the DEM receives its own continuous certificate.

This transfer warning concerns treating the approximate DEM as the law generating the monitored detector stream. If the observed detector vectors are generated by the declared exact categorical Stim circuit, the circuit-level e-factor applies to those vectors regardless of whether a downstream cached decoder graph was constructed from a decomposed approximate DEM. Keep these two probability models separate in any future experiment record.

Source/result: `gate_noise_mismatch_evalidity_audit.py`, `GATE_NOISE_MISMATCH_EVALIDITY_AUDIT.json`.

## Checkpoint 128 — conservative finite-time crossing bounds for the exact-circuit one-sided e-factors

`efactor_delay_concentration_audit.py` converts the checkpoint-122 continuous null-mean and alternative expected-log certificates into an Azuma-Hoeffding upper bound on the probability that a fixed one-sided process has not crossed by shot n. For `S_n = sum log L_t`, if every alternative shot has conditional expected log increment at least `mu` given the complete prior detector history and each log increment lies in a fixed interval of width `R`, then

`P(T > n) <= P(S_n < log(1/alpha)) <= exp(-2*(n*mu - log(1/alpha))^2/(n*R^2))`

when `n*mu > log(1/alpha)`. The first integer n satisfying this bound at most delta is a sufficient crossing quantile. Under the corresponding sustained null, Ville's inequality gives a one-sided ever-alarm probability at most alpha for the fixed e-process.

With the endpoint-chord-optimal lambdas from the prior exact certificate, the conservative sufficient n values for `(alpha, delta)=(.05,.10),(.05,.05),(.01,.10),(.01,.05)` are respectively `69,239; 89,719; 69,885; 90,366` shots upward and `150,462; 195,217; 151,419; 196,176` shots downward. The mean-drift-only crossing quotients are only 608/934 upward and 898/1,381 downward; these are explicitly not guaranteed delay calculations. The large gap is caused by the broad log-increment ranges and the distribution-free concentration inequality, especially for the asymmetric downward lambda.

These are analytic sufficient bounds, not expected or empirically observed delays. Conditions are a single fixed directional process, conditional per-shot laws remaining inside the declared exact categorical alternative rectangle, and the stated bounded increments. They do not cover resets, direction changes, the indifference band, false-switch control, practical rounding without outward-safe bounds, a DEM source law, or decoder utility. The initial smoke run had a wrong JSON-key assertion and wrote no result; the key was corrected, then the deterministic calculation and n/n-1 threshold checks passed. No detector histories or stochastic outcomes were generated.

Reproduction: `efactor_delay_concentration_audit.py`, `EFACTOR_DELAY_CONCENTRATION_AUDIT.json`.

## Checkpoint 130 — tighter continuous Freedman quantiles from certified mean ranges

A lower-cost variance bound avoids the unfinished full category-polynomial Bernstein transform. Let $W=\log(1+\lambda(Z/m_0-1))$ for $Z=X$ upward or $Z=1-X$ downward. On $Z\in[0,1]$, $W\in[a,b]$. The existing chord certificate gives a uniform conditional alternative lower mean $E[W\mid\mathcal F_{t-1}]\ge\mu$. Jensen and the continuous alternative upper bound on $E[Z\mid\mathcal F_{t-1}]$ give $E[W\mid\mathcal F_{t-1}]\le u$. Bhatia-Davis then gives

`Var(W | past) <= max_{m in [mu,u]} (b-m)(m-a) = v`,

and the centered increments satisfy `|W-E[W|past]| <= C=max(u-a,b-mu)`. Freedman’s lower-tail inequality yields

`P(T>n) <= exp(-(n*mu-A)^2/(2*(n*v + C*(n*mu-A)/3)))`, for `A=log(1/alpha)` and `n*mu>A`.

Using exact rational mean envelopes and endpoint-chord lambda values, with decimal outward slack, sufficient shot counts for `(alpha,delta)=(.05,.10),(.05,.05),(.01,.10),(.01,.05)` are `10,433; 13,232; 11,032; 13,839` upward and `3,787; 4,511; 4,503; 5,246` downward. Each saved bound at n is below delta, while the computed bound at n-1 is above delta. These are continuous-model, distribution-free *sufficient quantiles* for a single fixed directional process under sustained conditional alternative laws in the declared rectangle. They are neither expected delays nor observed alarms. The result improves the prior Azuma bounds but remains only a timing limit, not a product-level utility or graph-switch result.

The exact-rational full log-square category polynomial attempt from checkpoint 129 remains unfinished and is retained as such; it was not needed for this alternative derivation. Reproduction: `efactor_freedman_mean_range_bounds.py`, `EFACTOR_FREEDMAN_MEAN_RANGE_BOUNDS.json`.

## Checkpoint 131 — anytime mixture for one unknown abrupt change

The fixed one-sided e-factor can be extended to an unknown abrupt change time without resetting it. For each candidate start shot $s\ge1$, let $M_t^{(s)}=1$ before $s$ and multiply the certified one-step factor $L_i$ from $i=s$ through $t$. Choose the fixed prior $w_s=1/[s(s+1)]$, whose infinite sum is exactly one. The mixture $E_t=\sum_{s\ge1}w_sM_t^{(s)}$ is a nonnegative supermartingale under the corresponding sustained no-change null; Ville therefore gives `P(sup_t E_t >= 1/alpha) <= alpha`.

This particular prior has an exact constant-memory recurrence. Set `A_0=0`; for completed shot `t`, compute `A_t=L_t*(A_(t-1)+1/[t(t+1)])` and `E_t=A_t+1/(t+1)`. The second term is the exact remaining mass on candidate starts after t. An alarm observed after shot t can affect decoder use only from shot `t+1` onward. The recurrence was algebraically checked against direct mixture summation for three deterministic positive factor sequences, and the telescoping prior identity was checked exactly through 10,000 terms.

If the true abrupt transition starts at s and the alternative conditional law holds from s onward, `E_t >= w_s M_t^(s)`. This adds `log(1/w_s)=log(s(s+1))` to the component threshold. For alpha `.05` and miss target delta `.10`, the conservative Freedman post-change shot bounds are:

| Candidate start s | Prior weight | Upward bound | Downward bound |
|---:|---:|---:|---:|
| 1 | 1/2 | 10,693 | 4,099 |
| 1,000 | 1/1,001,000 | 15,248 | 9,422 |
| 1,000,000 | 1/1,000,001,000,000 | 19,611 | 14,556 |

These are sufficient analytic quantiles, not expected/observed delays. The direction must be fixed in advance from a trusted initial regime. The construction does not justify simply running upward and downward processes together: each has a different null rectangle. It handles one change alarm and a hold/lock decision only; it does not support reset, reversal, repeated transitions, parameter estimation, graph selection, or decoder benefit. Bursts in the indifference band and any conditional-law misspecification remain outside the guarantee.

Reproduction: `efactor_mixture_changepoint_delay.py`, `EFACTOR_MIXTURE_CHANGEPOINT_DELAY.json`; constant-memory equivalence tests: `test_efactor_mixture_recurrence.py`.

## Checkpoint 132 — finite-horizon uniform prior sensitivity

If deployment has a prespecified finite horizon $H$, a uniform prior `w_s=1/H` over candidate starts `s=1,...,H` reduces the late-start penalty relative to `1/[s(s+1)]`. For `t<=H`, maintain `A_t=L_t*(A_(t-1)+1/H)` and `E_t=A_t+(H-t)/H`; after H, set `A_t=L_t*A_(t-1)` and `E_t=A_t`. This is an O(1) update. The finite mixture is a nonnegative supermartingale under the same single directional no-change null, including after H, so its ever-crossing probability remains at most alpha. It provides a post-change component for every abrupt change starting by H, each with log threshold `log(H/alpha)`; it provides no component guarantee for a change beginning after H.

At alpha `.05` and delta `.10`, conservative Freedman post-change bounds across any start within H are:

| H (shots) | Upward bound | Downward bound |
|---:|---:|---:|
| 1,000 | 12,921 | 6,715 |
| 10,000 | 13,711 | 7,633 |
| 100,000 | 14,486 | 8,535 |
| 1,000,000 | 15,247 | 9,422 |

The horizon is an owner choice that changes the prior and coverage; these values are not an evaluation of actual delay. The infinite telescoping prior has no finite cutoff but incurs the start-dependent penalty shown at checkpoint 131. Both constructions remain one-change, one-direction alarms, not repeated or autonomous bidirectional decoder controllers. Reproduction: `efactor_horizon_prior_sensitivity.py`, `EFACTOR_FINITE_HORIZON_PRIOR_SENSITIVITY.json`.

## Checkpoint 133 — conservative fixed-point implementation sketch

For the exact one-change mixture, each detector shot contributes only one of six cofire counts, so its rational factor `L_t` can be selected from a six-entry table. A conservative fixed-point implementation can represent all positive quantities at scale `Q=2^96`, rounding every factor, start weight and remaining prior mass downward by integer floor. If `a_t/Q <= A_t`, then

`a_t = floor(l_t*(a_(t-1)+floor(Q*w_t))/Q)`

with `l_t=floor(Q*L_t)` preserves the invariant by induction. The reported lower mixture value is `(a_t+floor(Q/(t+1)))/Q`; its crossing implies that the exact rational mixture also crossed, so quantization can delay/miss alarms but cannot inflate the false-alarm probability. Compare the threshold using integer arithmetic (for alpha `a/b`, test `e_int*a >= Q*b`) rather than converting the state to float.

The deterministic audit exhaustively checked all `6^4=1,296` abstract factor-index sequences in each direction. For each of 5,184 sequence-prefixes per direction, fixed-point output was no greater than the exact mixture, and every lower-bound threshold crossing at alpha `.05` implied exact-mixture crossing. The maximum relative factor shortfall was `8.34e-30` upward and `3.01e-29` downward. The exact recurrence also matched direct component expansion for all 10,368 direction/prefix checks.

This is an arithmetic prototype, not a production implementation or validation of the physical e-factor premises. It does not address `t` overflow on fixed-width systems, outward-safe source constants across compilers, reset logic, or decoder action. Reproduction: `efactor_fixedpoint_mixture_audit.py`, `EFACTOR_FIXEDPOINT_MIXTURE_AUDIT.json`.

## Checkpoint 134 — expected-log growth within parts of the burst indifference band

The prior dead band `(p_b=.002,.010)` is an action/alternative-definition band, not wholly a no-evidence interval. Using the same gate-robust exact categorical mean polynomial over `p_m=[.001,.005]` and `p_g=[.002,.004]`, split the band into four subrectangles and use the concavity-chord lower bound plus Jensen upper bound for each fixed directional e-factor.

- Upward process: uniformly positive expected log growth is certified on `[.006,.008]` and `[.008,.010]`; sign is not certified on `[.002,.004]` or `[.004,.006]`.
- Downward-on-complement process: uniformly positive growth is certified on `[.002,.004]`; sign is not certified on the other three bands.

For a sustained conditional plateau within a sign-certified band, alpha `.05`, delta `.10`, and the infinite `1/[s(s+1)]` candidate-start prior, conservative post-change Freedman bounds at candidate starts `s=1,1,000,1,000,000` are:

| Direction and plateau | s=1 | s=1,000 | s=1,000,000 |
|---|---:|---:|---:|
| Upward `.006–.008` | 1,468,676 | 1,562,294 | 1,658,130 |
| Upward `.008–.010` | 22,510 | 31,248 | 39,642 |
| Downward `.002–.004` | 34,070 | 53,503 | 71,985 |

These are sufficient bounds for a plateau that begins at the candidate start and remains within its certified band; they do not bound a smooth path that traverses bands with unknown or negative drift. The mixture contains a start component at each shot, but does not retroactively erase prior drift inside that component. Positive evidence in an intermediate band does not prescribe a matching graph, and an alarm there may require hold/abstain rather than switching to an endpoint graph. Reproduction: `efactor_intermediate_band_expected_log.py`, `EF ACTOR_INTERMEDIATE_BAND_EXPECTED_LOG_BOUNDS.json`, `efactor_intermediate_band_delay.py`, `EFACTOR_INTERMEDIATE_BAND_DELAY_BOUNDS.json`.

## Checkpoint 135 — piecewise-certified linear ramps with endpoint dwell

A deterministic ramp screen applies the intermediate-band certificates to one explicit smooth path: midpoint-indexed linear `p_b` from `.002` to `.010` (up) or `.010` to `.002` (down) over R shots, followed by a sustained endpoint plateau. The candidate component starts when the path first enters a band with certified positive drift (`p_b=.006` upward; `.004` downward); earlier unclassified ramp observations are not credited or charged to that component. For varying per-shot parameter values within a band, the calculation sums per-shot conditional log-mean and variance lower/upper bounds and applies Freedman with the maximum centered-increment bound. The mixture prior weight uses the absolute candidate start shot.

At alpha `.05`, miss bound delta `.10`, and ramp beginning at global shot 1:

| Ramp length R | Upward high-end dwell needed | Downward low-end dwell needed | Total from ramp start (up/down) |
|---:|---:|---:|---:|
| 10,000 | 15,548 | 10,854 | 25,548 / 20,854 |
| 100,000 | 8,442 | 9,005 | 108,442 / 109,005 |
| 1,000,000 | 0 | 0 | 1,000,000 / 1,000,000 |

Starting the same ramps at global shot 100,001 changes the corresponding dwell values to 17,420/12,771; 9,034/9,566; and 0/0, reflecting the mixture prior's later-start penalty. Each number is a sufficient conditional probability bound for this specified piecewise ramp and endpoint hold. It is not a universal smooth-drift guarantee: arbitrary paths can spend time in uncertified bands, change nuisance parameters outside the rectangles, or stop before enough positive evidence accumulates. This remains detector-law evidence only; no action mapping or decoder utility is established. Reproduction: `efactor_linear_ramp_delay_screen.py`, `EFACTOR_LINEAR_RAMP_DELAY_SCREEN.json`.

## Checkpoint 136 — alpha spending across externally re-baselined episodes

Repeated one-change alarms can receive a global false-switch budget only if each new episode begins from a trusted baseline whose corresponding directional null is conditionally valid. A simple exact allocation is `alpha_j=alpha_total/[j(j+1)]`, whose sum over episodes is exactly `alpha_total`; a union bound across episode-level Ville guarantees does not require independence. For each episode, run one preselected direction and one change-time mixture. After its single alarm, hold/lock and require independent external re-baselining before starting a new episode. The alarm itself does not prove the post-alarm regime, so using it to launch the opposing process is not covered.

With total alpha `.05`, delta `.10`, the infinite candidate-start prior, and candidate change start `s=1,000`, the sufficient post-change shot bounds for episode indices `j=1,2,10,100` are `15,474; 15,832; 16,767; 18,192` upward and `9,687; 10,105; 11,200; 12,877` downward. Later episode indices spend less false-switch budget and therefore raise the threshold. This does not grant autonomous repeated switching: if an episode's baseline is selected from a potentially false alarm, its new null may be invalid and the union guarantee no longer applies. Reproduction: `efactor_external_epoch_alpha_spending.py`, `EFACTOR_EXTERNAL_EPOCH_ALPHA_SPENDING.json`.

### Checkpoint 137 — finite fixed-point prior coverage horizon
The Q=2^96 down-rounded infinite-prior recurrence has a mathematically finite change-start coverage limit: `floor(Q/[s(s+1)])` is nonzero through `s=281,474,976,710,655` and zero beginning at `s=281,474,976,710,656`. False-alarm conservatism is retained by the lower-bound process, but the zero-weight starts have no detection-delay guarantee; the quantized implementation must not be described as an exact infinite-horizon detector. At s=1,000 and 1,000,000, the additional log-threshold penalty from weight rounding is approximately `5.38e-24` and `5.21e-18` nats, respectively. At s=10^12 it is about `2.05e-6` nats. These values show negligible rounding penalty across plausible development horizons, while identifying the finite cutoff. A prespecified finite-H uniform prior avoids that particular start-weight tail issue when H is representable. Reproduction: `efactor_fixedpoint_prior_horizon.py`, `EFACTOR_FIXEDPOINT_PRIOR_HORIZON.json`.

## Checkpoint 138 — finite lambda bank for unknown effect size

The endpoint-tuned single lambda was conservative but poorly matched to parts of the intermediate burst band. A finite bank can address that without an online p estimate: for each continuous target region, choose a fixed rational lambda by rounding down the endpoint-chord optimum based on that region's certified mean lower bound. Use four lambdas per direction with equal weight 1/4, then combine each lambda's change-time mixture with the prior `w_s=1/[s(s+1)]`. Because each fixed-lambda process is an e-process under the same directional null, both convex-mixture layers preserve null validity. The component supporting a delay bound has prior mass `w_s/4`, adding `log 4` to its threshold.

At candidate start `s=1,000`, alpha `.05`, delta `.10`, continuous exact-circuit Freedman bounds are:

| Direction | Burst region | Lambda | Sufficient shots |
|---|---:|---:|---:|
| Up | `.004–.006` | `.001070` | 289,572 |
| Up | `.006–.008` | `.003019` | 46,517 |
| Up | `.008–.010` | `.004968` | 20,974 |
| Up | `.010–.018` | `.006917` | 15,700 |
| Down | `.006–.008` | `.132780` | 391,256 |
| Down | `.004–.006` | `.320656` | 61,091 |
| Down | `.002–.004` | `.508533` | 21,669 |
| Down | `0–.002` | `.696410` | 9,951 |

The bank certifies positive growth in all four listed regions per direction under the exact balanced circuit, measurement and gate rectangles. This includes previously uncertified regions for the single endpoint-tuned lambda. The delay numbers remain sufficient model-conditional quantiles, not actual detections. A bank uses four per-lambda mixture states per direction and gives no permission to run both directions under mismatched nulls. The monitor still does not estimate burst probability or show that any graph is beneficial at the alarm point. Reproduction: `efactor_lambda_bank_feasibility.py`, `EFACTOR_LAMBDA_BANK_FEASIBILITY.json`.
