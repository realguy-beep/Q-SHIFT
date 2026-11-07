# Candidate allocation, power, and resource projections

## Counts

Each root uses 2,000 calibration and 2,500 paired evaluation shots. Across five conditions, the candidate allocations are:

| Roots per condition | Total roots | Calibration shots | Evaluation shots | Total unique shots |
|---:|---:|---:|---:|---:|
| 578 | 2,890 | 5,780,000 | 7,225,000 | 13,005,000 |
| 640 | 3,200 | 6,400,000 | 8,000,000 | 14,400,000 |
| 666 | 3,330 | 6,660,000 | 8,325,000 | 14,985,000 |

The statistical design simulations did not consume these shots. They generated only root-effect vectors in bounded batches. Runtime was 789.64 seconds; maximum array payload in a single 256-replicate batch at n=666 is about 5.1 MiB. Process high-water RSS was not captured for this run, and must not be reported as measured.

## Full Stim/PyMatching pipeline projection

The already completed, separate disposable benchmark processed 225,000 unique shots across 50 roots in 6.478 seconds (34,733 shots/s), with measured peak RSS 85,737,472 bytes and 479,697 compressed archive bytes. Linear projections are:

| Candidate total | Projected wall time | Projected compressed archives | Projected raw evidence payload |
|---:|---:|---:|---:|
| 13.005M | 374.6 s (6.24 min) | 27.7 MB | about 549 MB |
| 14.400M | 414.6 s (6.91 min) | 30.7 MB | about 608 MB |
| 14.985M | 431.5 s (7.19 min) | 32.0 MB | about 633 MB |

These are engineering extrapolations from a small separate development run, not a guarantee. The benchmark's 7-root pause and restart completed with checkpoint hashes preserved, and its independent auditor re-decoded all 50 roots. The historical v2 auditor remains fixed at 100 roots/condition and cannot audit the candidate allocation without a new versioned, parameterized auditor.

## Statistical feasibility

The scenario-envelope calibrated studentized test passed null size and bound-coverage criteria at all three n values. However, the predeclared 80% lower-Wilson power criterion at true Δ=−0.0003 under 1.5× variability failed even at 666 roots. At 2× variability, power is only 56.7–58.3%. The apparent high power at −0.0004 is not a justification to redefine the target after the simulation.
