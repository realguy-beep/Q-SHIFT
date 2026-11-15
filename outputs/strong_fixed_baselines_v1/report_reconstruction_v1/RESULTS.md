# Strong fixed-baseline development v1 — protocol-consistent reconstruction

**Status:** development feasibility analysis with a disclosed runner deviation; not confirmatory.

The runner's original pooled-static estimate used generating-condition labels while fitting its profiles, contrary to the protocol. This report uses the protocol-specified independent template profiles and pooled detector rows. The original run files and legacy pooled predictions are preserved; the legacy arm is summarized separately.

- Unique study shots verified: 3,660,000
- Paired final development shots: 1,500,000
- Final roots: 600
- Pooled detector-static estimated burst p: 0.00804
- Safety-constrained static p: 0.000

## Paired final-development LER by condition

| Burst probability | Shots | Nominal | Pooled static | Safety static | Adaptive | Privileged reference |
|---:|---:|---:|---:|---:|---:|---:|
| 0.000 | 300,000 | 0.481333% | 0.527000% | 0.481333% | 0.482000% | 0.481333% |
| 0.004 | 300,000 | 0.573000% | 0.532667% | 0.573000% | 0.531333% | 0.532000% |
| 0.008 | 300,000 | 0.707333% | 0.590333% | 0.707333% | 0.591000% | 0.590333% |
| 0.012 | 300,000 | 0.781333% | 0.582000% | 0.781333% | 0.580000% | 0.580000% |
| 0.016 | 300,000 | 0.841000% | 0.564000% | 0.841000% | 0.555000% | 0.555333% |

## Primary descriptive comparison

Equal-condition adaptive − safety-static difference: **-0.1613333%**, root-bootstrap 95% interval [-0.1702500%, -0.1524167%].

No confirmatory p-values are reported. The interval reflects root resampling within these five simulated conditions and is not a hardware or external-generalization claim.

## Interpretation limits

The safety-static baseline is selected using separate development labels and validated on a distinct p=0 subset; the pooled static baseline uses detector-only calibration. Adaptive uses per-root detector-only calibration. The privileged reference receives the true simulated p and is not deployable. All decoders score identical per-root final detector/observable arrays. Stage 5 evaluation material was not accessed.

Independent audit input SHA-256: `f70c969fb3cb29283603755c84eee6f51dbce38cdc308901eed59fb3bcca0b09`.


## Legacy runner pooled arm (invalid for the frozen comparison)

The runner recorded p=0.00831, while the protocol-consistent template-only estimate is p=0.00804. The legacy per-condition rates and paired disagreements are in `PER_CONDITION.csv` and `PER_ROOT.csv`. They are not included in the corrected fixed-vs-adaptive contrasts.
