# Belief-matching Phase A: build and verification results

**Gate outcome: FAIL for the serial variants (BM1–BM3); PASS for BM0.** Under the plan, Phase A stops here and reports before any screening. No Phase B decode has been run.

## Build

- **`bm.py`:** BP (ldpc 2.4.1 `BpDecoder`) runs on the hypergraph DEM, and its posteriors re-weight a PyMatching graph. Both the hypergraph and the matching graph come from **one decomposed stim DEM**, so they are consistent by construction.
- **Edge rule (deviation from the draft plan):** the plan's Higgott rule was the sum p_e = Σ p̂_h. The build uses the exact independent-merge rule instead, p_e = ½(1 − Π_{h∋e}(1 − 2p̂_h)). It is the rule PyMatching itself uses to merge parallel DEM edges, which makes the identity test exact. For small p̂ the two rules agree to first order.
- **Structure:**

  | | d=3 | d=5 | d=7 |
  |---|---:|---:|---:|
  | Error instructions | 591 | 1,974 | 4,181 |
  | Matching edges | 142 | 507 | 1,083 |

  All components are graphlike, and no edge has conflicting logical bits.

## Tests (`tests/test_bm.py`: 7 of 7 pass)

- **Mapping consistency (d=3, 5, 7):**
  - every hyperedge column equals the XOR of its edges;
  - logical bits are consistent;
  - every edge has 1 or 2 detectors.
- **Prior edge probabilities equal PyMatching's** `from_detector_error_model` edge probabilities, at d=3, 5 and 7, within 1e-9 relative.
- **Identity:** with BP off, BM's predictions equal plain uncorrelated PyMatching **bit for bit**. This was checked on 400 deterministic syndromes at each of d=3, 5 and 7.
- **Other checks:** the sign-parity rule holds for posteriors above ½; when the BP-converged shortcut is taken, its correction reproduces the syndrome; zero syndromes decode to 0; all variants build.

## d=3 quality vs exact (72,000 already-exposed V1.5 development rows; 24,000 per q)

| Arm | q=0 | q=0.01 | q=0.02 | Share of exact's nonzero gain over Astar |
|---|---:|---:|---:|---:|
| Astar (saved) | 200 | 284 | 381 | — |
| Exact (saved) | 91 | 125 | 123 | 100% |
| BM0 (parallel) | 126 | 164 | 186 | 76% |
| **BM1 (serial)** | 118 | 154 | 150 | **87%** |
| BM2 (serial + converged shortcut) | 118 | 154 | 150 | 87% (same predictions as BM1) |
| BM3 (serial, q_dec 0.0025) | 115 | 158 | 184 | 77% |

Belief-matching recovers 76–87% of the exact decoder's gain at d=3, and the serial schedule is clearly better. These are development rows that V3 has already used.

## Cost (rehearsal-only shots, single process; error counts on these rows have no decision role)

| ms/shot | BM0 | BM1 | BM2 | BM3 |
|---|---:|---:|---:|---:|
| d=5 (3 × 1,000 Phase 2 rehearsal shots) | 3.3–4.9 | 29–45 | 28–43 | 30–36 |
| **d=7** (1,000 screen-rehearsal shots) | **22.4** | **214** | **208** | **185** |

**Gate:** at most 50 ms/shot at d=7. BM0 passes; BM1–BM3 fail by about 4×.

### Diagnosis (200 d=7 rehearsal shots)

- **The graph rebuild is not the bottleneck.** It takes 0.2 ms per shot.
- **The cost is ldpc's serial BP schedule:** 111 ms/shot for 11.2 mean iterations, against 8.3 ms for parallel BP over 16.9 iterations. That is about 20× more per iteration.
- The same cost explains why L2 (serial BP+OSD) took about 129 ms at d=7 in the screen.

## Consequences

- **The serial variants are not affordable as planned.** Phase B with BM1–BM3 would take about 600,000 × 3 × 0.2 s / 8 ≈ 12 h. A powered Phase C at d=7 (1.22 M shots) would take about 8–9 h for one serial arm alone.
- **BM0 is affordable** (about 22 ms/shot at d=7), but at d=3 it recovers less of the exact gain (76% vs 87%).
- Choosing among the options below changes the pre-registered variant set, so it needs owner sign-off before Phase B.
