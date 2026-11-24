# IDENT1 stage 1 results

Freeze b49a940be, protocol with A1 and A2. F0 and F1; F2 was not run. Two runs, 416 s and 418 s, peak 6.8 GB private memory. **All eight result files are byte-identical** (`REPEAT_HASHES.json`; only the timing log differs). No sampling. HELD (1,297 classes) was not computed.

Named check passed: X09 against B gives λ = 28.23, D117 = 3.5063% and D117/D119 = 1.3487%, as DB8 and Codex published.

**Scope:** analytic, model-conditional, not independently audited. It gives no error rates, harm or controller performance. M3 and HARMFUL are withheld (the harm proxy failed its check). DB8 stays VOID with numerical NO ADVANCE; CF2 stays NOT CONFIRMED.

## Predeclared reading (section 7)

**"F1 separates, M2 also rejects: pair features are worth a prospective rule."** It applies to most DESIGN classes, not all, and only within the nuisance grid. The limits below matter as much as the reading.

## Headline, DESIGN, n = 2,000 rows, bank state anywhere on the grid, X at nominal

| | F0 single detectors | F1 with local pairs |
|---|---|---|
| Weight 1-3: not SEPARATED from some state (M1) | 7 of 418 | 0 of 418 |
| Weight 1-3: accepted as some bank state (M2 > 5%) | **266 of 418** | **16 of 418** |
| Weight 4: not SEPARATED from some state | 2 of 764 | 0 of 764 |
| Weight 4: accepted as some bank state | **178 of 764** | **1 of 764** |
| Smallest J over all pairs | 17.1 | 62.1 |

- No pair is AMBIGUOUS (J < 10.8) at these settings.
- All 9 MARGINAL class/state pairs under F0 become SEPARATED under F1, and no pair has a smaller J under F1.
- SEEN (84): accepted by some state 59 under F0 and 9 under F1. This includes the four bank states themselves.
- At n = 4,000 rows the accepted counts fall to 35 and 7 (F0), and 6 and 0 (F1), for weights 1-3 and 4.

**So with single detectors the information is mostly there, but an open-set test does not use it.** M1 assumes the alternative is known; M2 does not, and spreads its power over 120 directions.

## The DB8 states (SEEN; descriptive)

| State, against | F0: J | F0: P(accepted) | F1: J | F1: P(accepted) |
|---|---|---|---|---|
| X09 vs B | 23.3 | **0.83** | 201.5 | < 0.0001 |
| E vs A | 57.2 | 0.072 | 210.6 | < 0.0001 |
| V06 vs B | 52.3 | 0.14 | 234.1 | < 0.0001 |
| X03 vs B | 54.5 | 0.12 | 249.9 | < 0.0001 |

M2's test is a covariance-weighted cousin of DB8's fit rule, not the same rule, so these are not DB8's acceptance rates. In this model X09 and B are **not** indistinguishable. Protocol DB8's word "undetectable" is not supported, as Codex said.

## Exact look-alikes (Q1)

- 827 of 2,563 classes hold supports needing opposite corrections (86 of 1,003 when limited to weight 1-3). Detector data of any kind cannot tell those supports apart.
- Bank state A (20, 29, 38) shares its class with two opposite-flip supports of weight 2: **(9, 47) and (9, 49)**. B, C and D have none of weight 1-3. With weight 4, all four have some (15, 8, 9, 2).
- A detector-only controller acting on A therefore cannot exclude those two bursts. How likely they are is outside this study.

## Limits that qualify the reading

1. **Most minima sit on the edge of the nuisance grid:** 4,495 of 5,910 class/state pairs under F0 and **5,694 of 5,910 under F1**. The worst bank-state point is usually the lowest burst strength (q = 0.005), and under F1 often the edge in p too. A wider grid would lower J, by an unknown amount. The ranges were fixed in advance and were not widened after seeing this.
2. **Weak unknown bursts are much harder.** When X also varies over the grid (F0 only, A2), 695 of 1,182 DESIGN classes and 70 of 84 SEEN are not SEPARATED from some state; the smallest J is 4.8. X09 against B falls to 5.6. **The same pass was not computed for F1**, so nothing here says pairs survive a weak burst.
3. **F1's M2 is unvalidated.** The Gaussian check covered single detectors. Pairs co-fire rarely (0.4% is about 8 counts in 2,000), and M2 uses a χ² with 2,138 degrees of freedom and the bank state's covariance only. Its F1 noncentralities (about 1,000) are several times J, which shows the covariances differ. Treat F1 acceptance probabilities as indications.
4. M1 uses a known alternative and exact covariances. A real controller has neither.
5. 16 weight 1-3 classes and 1 weight 4 class are still accepted under F1.
6. Counts are over enumerated supports, not probabilities that such bursts occur. DESIGN holds two symmetry partners together, so classes are not independent.
7. HELD is untouched. The choice to pursue pairs has now been made on DESIGN and SEEN.

## What this does not settle

Whether acting on an ambiguous state is harmful; whether a causal pair-based rule works; whether F1 survives weak bursts or a wider background range; hardware, drift, other distances.

## Files

`results/stage1_run1/` (committed), `results/stage1_run2/` (local, identical), `REPEAT_HASHES.json`.
