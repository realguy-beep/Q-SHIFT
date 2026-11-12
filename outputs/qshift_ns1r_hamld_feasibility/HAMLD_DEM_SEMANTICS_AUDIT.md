# HAMLD / Q-SHIFT DEM semantics audit

## Outcome

The pinned HAMLD `DetectorErrorModelHypergraph` parser **structurally round-trips Q-SHIFT's undecomposed approximate DEM** at burst probabilities 0 and .01. This is a parser-level result; it is not a decoder-inference result. The compiled package remains unavailable, so probability-to-prediction semantics, logical-class inference and boundary decoding are not validated.

## Q-SHIFT model and deterministic DEM construction

Inputs are only the explicit circuit builders:

- `outputs/phase2b_pauli_bias/noise_model.py::build_circuit`
- `outputs/phase3a_correlated_noise_preflight/simulator.py::build_spatial_burst_circuit`

The fixed circuit is balanced categorical 1Q/2Q gate noise `.003`, measurement flips `.003`, rotated Z memory at d=3 / five rounds. Burst injection is a simultaneous X error on data qubits (8,10) after each of five `MR` boundaries. We built only Stim circuit and DEM objects under Python 3.10.18 / Stim 1.16.0; no sampler was compiled or called.

For `decompose_errors=False, approximate_disjoint_errors=True`:

| Burst p | Detectors / observables | DEM error mechanisms | HAMLD hyperedges | Exact ordered targets and decimal p preserved | Duplicate signatures | Single-D mechanisms (D-only / D+L) | Multi-D hyperedges | Max D degree | L-bearing |
|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 0 | 40 / 1 | 443 | 443 | yes / yes | 0 | 40 (28 / 12) | 403 | 4 | 71 |
| .01 | 40 / 1 | 448 | 448 | yes / yes | 0 | 40 (28 / 12) | 408 | 4 | 71 |

All 41 graph nodes were ordered `D0…D39,L0`. The DEM instruction stream consisted only of 40 detector annotations and error instructions: no repeat blocks, `shift_detectors`, or separator targets. This absence is established for the Q-SHIFT circuit after its builder calls `.flattened()`; it is not a claim that the parser supports arbitrary nested Stim DEM syntax.

The five additional p=.01 signatures relative to p=0 are `D8 D10`, `D16 D18`, `D24 D26`, `D32 D34`, and `D36 D38`, each with DEM probability .01 and no L0 target. These are the five per-round injection mechanisms. All 443 common signatures retain the same probability between p=0 and .01. Other categorical gate mechanisms remain part of the same DEM.

## Parser round-trip method

`deterministic_hamld_dem_roundtrip.py` imports the exact pinned `src/hamld/contraction_strategy/dem_to_hypergraph.py` class and compares, in original order, each Stim error instruction's D/L target tuple and textual Decimal probability against the produced hyperedge and weight. A minimal package-path shim skips upstream `hamld/__init__.py` solely because it imports the unbuilt extension; no decoder class is imported or substituted. All comparisons passed for both DEMs. The script also checks detector/L0 node IDs, duplicate signatures, and repeat/shift absence.

The pinned parser uses DEM `error(p)` values directly. The normal Python contraction executor branches each edge with probabilities p and `1-p`, so it interprets these weights as independent Bernoulli mechanism probabilities, not PyMatching log-odds. This is consistent with the *DEM's* independent-mechanism representation. It does not make the approximate DEM equal to the original categorical circuit distribution.

## Limits and decomposed DEM

The original circuit includes 15 mutually exclusive non-II Pauli outcomes per two-qubit `PAULI_CHANNEL_2` location. Stim rejects DEM conversion without `approximate_disjoint_errors=True`; hence both the HAMLD undecomposed DEM and Q-SHIFT's decomposed PyMatching DEM include a disjoint-event approximation. The two conversions are nevertheless different representations.

Do not pass the decomposed PyMatching DEM to this parser: its `^` separator tokens are skipped and all D/L targets are collected into one hyperedge. The tested decomposed nominal DEM had 586 error instructions, 444 with separators. The round-trip result above applies only to the specified undecomposed input.

The circuit's sole observable is `OBSERVABLE_INCLUDE(0) rec[-7] rec[-8] rec[-9]`, i.e. L0 is the XOR parity of those three final record bits. Parser round-trip proves the L0 target IDs survive; it does not prove that HAMLD's decoder returns the same predicted-observable convention. HAMLD's one-observable output path is dimensionally compatible, but actual prediction semantics require the missing build and deterministic decoder tests.
