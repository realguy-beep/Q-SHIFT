# Exact-MAP and new-decoder opportunity

## Results that are genuinely exact

The categorical feasibility phase implements mutually exclusive categorical fault outcomes and exact summation over small toy fault configurations. Independent Stim forced-outcome enumeration matched all 320 tested toy configurations, with a deterministic tie rule. The work is technically useful as a correctness reference, and toy examples show that standard or correlation-aware PyMatching on an approximate DEM can choose a different logical decision from categorical MAP.

This exactness is confined to the toys. The Phase 2C “reference forest” is a sample-trained posterior surrogate, not an exact conditional likelihood decoder. On 120,000 paired pilot shots it made 2,579 errors (LER 2.149%) versus 628 for the regime-matched Phase 2B PyMatching arm (0.523%). Its calibration-selected regime-informed and fixed forest arms tied because calibration chose the same model in each basis. The result shows model/prediction differences, not a demonstrated benefit from a more faithful decoder.

## Reduced-round structured inference and DEM representation

The categorical surface-fragment investigation validated exact inference for selected small instances. A dense frontier reached 512 states at one round, 131,072 at two rounds, and 33,554,432 at three rounds. Three-round inference completed in about 89 seconds with a 764 MB peak working set. The dense 4-round joint array would require about 64 GiB; the 5-round, 40-detector version about 16 TiB. The original d=3/r=5 categorical fault assignment count was `2^609`; direct enumeration is infeasible.

The matching-representation investigation found a valid local graphlike event rewrite that preserves the full event probability and logical parity for events with at most two detectors. This repaired an exact toy discrepancy. The rule rejects non-graphlike hyperedges/logical-only faults; the full target five-round DEM contains many three- and four-detector events. Local restricted posterior refinement covered only about 10.5% of one-round syndromes and fell back on the rest; no full-circuit exact decoder resulted.

## Interpretation

The exact-to-matching toy gap proves that representation can matter on bounded examples. It does not quantify full-circuit decoder regret. Phase 2C does not isolate DEM approximation because its fitted surrogate is both weaker and imperfectly calibrated. The reduced-round tests indicate a severe scaling boundary for dense exact methods and no validated scalable structured inference method at the target five rounds.

There is a technically interesting *decoder-representation* question, but it is not yet a credible adaptive-headroom opportunity. A new decoder study would need to show a scalable, semantically faithful inference method that improves paired logical outcomes over the strongest fixed PyMatching baseline on development circuits before any adaptation experiment. Current evidence does not justify that work as the next experiment under the user's bounded feasibility gate.

