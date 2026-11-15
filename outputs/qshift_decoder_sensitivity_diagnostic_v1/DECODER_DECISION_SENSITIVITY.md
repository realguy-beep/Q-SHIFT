# PyMatching decision sensitivity

## Decoder reconstruction

The deterministic reconstruction uses the Phase 3A `build_spatial_burst_circuit` source at the reference commit. Configuration: rotated `surface_code:rotated_memory_z`, distance 3, five rounds, balanced within-gate Pauli composition, gate probability 0.003, measurement probability 0.003, bias ratio 10, burst pair `(8,10)`, and burst probabilities `0, 0.004, 0.008, 0.012, 0.016`. DEM conversion uses `decompose_errors=True` and `approximate_disjoint_errors=True`; each matcher is built with `enable_correlations=True`, and each `decode_batch` call also passes `enable_correlations=True`.

The pooled fixed matcher uses the detector-only calibration estimate `p_global=0.008004311733110277`. The profile matcher uses each saved root's 40-feature calibration estimate. The true-`p` matcher uses the known condition parameter and is a privileged reference only. These are reconstructed models, not a new outcome-based selection. All three receive the same detector rows for a given condition/root.

## Label-free prediction disagreement

| Burst probability | Evaluation detector rows | Pooled vs profile changed predictions | Pooled vs true-p changed predictions |
|---:|---:|---:|---:|
| 0 | 20,000 | 0 (0.00000%) | 3 (0.01500%) |
| 0.004 | 20,000 | 0 (0.00000%) | 5 (0.02500%) |
| 0.008 | 20,000 | 0 (0.00000%) | 0 (0.00000%) |
| 0.012 | 20,000 | 0 (0.00000%) | 4 (0.02000%) |
| 0.016 | 20,000 | 0 (0.00000%) | 1 (0.00500%) |

The five conditions comprise 100,000 detector rows. The nonzero conditions comprise 80,000 rows, of which only 10 predictions differ between fixed pooled and true-`p` matchers (0.0125%). Since no evaluation observable member was loaded, neither the direction of any changed prediction nor an LER effect is known. On these exact 80,000 rows, at most 10 error indicators could differ, so the maximum possible absolute aggregate LER change is `10/80,000 = 0.000125`. This is a bound on the observed prediction difference, not a confidence interval or a claim that the oracle helps.

## Edge-weight evidence

The deterministic DEM contains five burst pair components: `D8 D10`, `D16 D18`, `D24 D26`, `D32 D34`, `D36 D38`. At `p=0`, all five edges are absent from the true-`p` graph; the graph has 142 edges versus 147 in the pooled graph. At each nonzero `p`, both graphs contain 147 edges; the only changed common-edge weights are the five burst edges. The other 142 edge weights are unchanged.

| True burst p | Pooled burst-edge weight | True-p burst-edge weight | Absolute change |
|---:|---:|---:|---:|
| 0 | 4.819738 | absent | removed |
| 0.004 | 4.819738 | 5.517453 | 0.697715 |
| 0.008 | 4.819738 | 4.820282 | 0.000543 |
| 0.012 | 4.819738 | 4.410776 | 0.408962 |
| 0.016 | 4.819738 | 4.119037 | 0.700701 |

Therefore `p` does affect the graph model: it changes weights on the intended correlated pair edges, substantially at the endpoints. Yet those changes rarely alter the selected correction in the saved detector rows. The estimated profiles sit near 0.008, and their matchers reproduce every pooled prediction in this diagnostic. This identifies both an estimator bottleneck and, more decisively, a decoder decision-sensitivity bottleneck.

## Interpretation limits

- Disagreement counts are deterministic comparisons on the already saved evaluation detector arrays; they are not new samples and not a statistical performance test.
- The 10/80,000 nonzero disagreement count has no outcome direction without labels. No logical error counts, rates, confidence intervals, or claims of improvement are reported.
- The result applies to this distance-3, five-round circuit, these saved detector rows, the specified DEM approximation and PyMatching correlation mode. It does not show all correlated-noise models are insensitive to adaptation.
- The five pair events are graphlike in this construction and are explicitly represented as edges. The result does not validate exact-circuit-to-DEM equivalence beyond the declared approximation.
