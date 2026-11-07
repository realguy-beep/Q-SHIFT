# Reduced-round scaling benchmarks

All fragment runs use distance 3, rotated Z-memory, X-biased native Pauli channels, gate p=0.003 and measurement p=0.003. No noisy batches or Phase 2B evaluation shots were generated. Fault masks were extracted by deterministic one-hot propagation. Rounds 1–4 use the frozen generator/channel replacement with only the round count varied; rounds 5 call the frozen Phase 2B builder unchanged.

| Rounds | Detectors | Fault locations | Full categorical configurations | Frontier bits / states | Dense float64 joint size | Inference | Inference time | Runner wall time | Peak working set | Forced nonidentity checks |
|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| 1 | 8 | 49 | `2^129` | 9 / 512 | 4 KiB | Completed | 0.0016 s | 1.02 s | 36.1 MB | 401 |
| 2 | 16 | 89 | `2^249` | 17 / 131,072 | 1 MiB | Completed | 0.174 s | 3.14 s | 41.9 MB | 793 |
| 3 | 24 | 129 | `2^369` | 25 / 33,554,432 | 256 MiB | Completed | 89.09 s | 95.46 s | 764.1 MB | 1,185 |
| 4 | 32 | 169 | `2^489` | 33 / 8,589,934,592 | 64 GiB | Skipped before allocation | — | 10.10 s | 37.8 MB | 1,577 |
| 5 | 40 | 209 | `2^609` | 41 / 2,199,023,255,552 | 16 TiB | Skipped before allocation | — | 15.31 s | 38.8 MB | 1,969 |

The largest completed inference was the three-round fragment. It scored all 16,777,216 detector syndromes, normalized to 1 within float64 error, and returned exact-MAP Bayes risk 0.00371937 for this one specified circuit channel. This is a calculated reference risk, not a sampled benchmark, cross-decoder comparison, or distance-scaling claim.

The five fragment-run wall times sum to 125.03 seconds. Across all five circuits, 5,925 nonidentity one-hot fault outcomes were propagated, with two repeated deterministic sampler rows per case. The earlier toy phase separately checked 320 deterministic categorical configurations. Total stochastic shots generated in this investigation: zero.

Peak working set was sampled from the Windows process API at 20 ms intervals. The three-round measured peak was 764,133,376 bytes (< 2 GiB). Skipped four- and five-round runs only extracted masks and constructed metadata; no large posterior arrays were allocated. Per-round raw effect masks and summary values are saved in `FRAGMENT_R1.json` through `FRAGMENT_R5.json` (and `FRAGMENT_R3_EFFECTS.json` through `FRAGMENT_R5_EFFECTS.json`).

