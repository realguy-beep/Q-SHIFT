# DEM construction feasibility audit

## Decision scope

This audit attempts the exact two conversion settings in the proposed follow-up on all six frozen Phase 2B conditions. It constructs circuits and DEMs only; it generates **zero simulation shots** and does not write to the pilot, Phase 2B, or prior audit directories.

Command run from `outputs/dem_feasibility_gate/`:

```powershell
python -m py_compile audit_dem_construction.py
python audit_dem_construction.py
```

Both commands completed successfully as audit programs. The program caught and saved all six B-conversion exceptions in `DEM_CONSTRUCTION_RESULTS.json` rather than aborting at the first condition.

## Software

- Python 3.12.10
- Stim 1.16.0
- PyMatching 2.4.0
- NumPy 2.5.3

## Conversion results

| Condition | Circuit | A: decompose + approximate disjoint | A detectors / observables | A error mechanisms / `^` separators | A PyMatching correlation off/on | B: decompose, no approximation |
|---|---|---|---:|---:|---|---|
| X-memory / X-biased | PASS | PASS | 40 / 1 | 578 / 564 | PASS / PASS | **FAIL: ValueError** |
| X-memory / balanced | PASS | PASS | 40 / 1 | 578 / 564 | PASS / PASS | **FAIL: ValueError** |
| X-memory / Z-biased | PASS | PASS | 40 / 1 | 578 / 564 | PASS / PASS | **FAIL: ValueError** |
| Z-memory / X-biased | PASS | PASS | 40 / 1 | 586 / 572 | PASS / PASS | **FAIL: ValueError** |
| Z-memory / balanced | PASS | PASS | 40 / 1 | 586 / 572 | PASS / PASS | **FAIL: ValueError** |
| Z-memory / Z-biased | PASS | PASS | 40 / 1 | 586 / 572 | PASS / PASS | **FAIL: ValueError** |

For A, all DEM detector coordinates exactly matched the generated circuit coordinates; detector IDs were 0–39 and the sole observable ID was L0. The generated circuit contains 40 detectors and one observable in each condition. A produced finite mechanism probabilities in [0,1]. PyMatching constructed 40-node, 142-edge, one-fault-ID graphs in both correlation modes for every condition. Edge/weight/fault-ID signatures matched between modes, and a deterministic all-zero syndrome decoded to `[0]` in both modes. Thus the correlation-aware API is usable with A. These checks establish software compatibility, not physical exactness.

The following probability summaries refer to DEM error-record probabilities, not the total categorical channel probability. They must not be summed and interpreted as a per-gate physical fault rate.

| Condition | A mechanisms | Minimum record p | Median record p | Maximum record p |
|---|---:|---:|---:|---:|
| X-memory / X-biased | 578 | 0.0000178571 | 0.000196429 | 0.0167283844 |
| X-memory / balanced | 578 | 0.000200000 | 0.000400000 | 0.0085458395 |
| X-memory / Z-biased | 578 | 0.0000178571 | 0.000196429 | 0.0093805763 |
| Z-memory / X-biased | 586 | 0.0000178571 | 0.000196429 | 0.0092052925 |
| Z-memory / balanced | 586 | 0.000200000 | 0.000400000 | 0.0112898861 |
| Z-memory / Z-biased | 586 | 0.0000178571 | 0.000196429 | 0.0174402816 |

## Exact B failure

The identical frozen circuit object was passed to B with only `approximate_disjoint_errors=False`. All six calls raised `ValueError`. The common exception text was:

```text
Encountered the operation PAULI_CHANNEL_2 during error analysis, but this operation requires the `approximate_disjoint_errors` option to be enabled.
If you're calling from python, using stim.Circuit.detector_error_model, you need to add the argument approximate_disjoint_errors=True.
```

The complete exception strings and Python tracebacks, including channel parameters and Stim circuit stack location, are preserved for each of the six conditions in `DEM_CONSTRUCTION_RESULTS.json`. X-memory errors identify TICK layer 34/36 and instruction 45; Z-memory errors identify TICK layer 34/36 and instruction 44. The failure occurs during Stim's DEM conversion, before a B DEM exists; therefore B detector/observable DEM definitions, probability records, separators, or PyMatching graphs cannot be compared or decoded.

Stim 1.16.0's local `Circuit.detector_error_model` documentation explains the result: with the flag false, disjoint components in a composite channel can cause an exception because a DEM contains independent mechanisms; with the flag true, the disjoint cases are approximated as independent. The failure is expected behavior for these categorical `PAULI_CHANNEL_2` instructions, not a PyMatching graph-construction failure.

## Semantic conclusion

A is constructible, but it is an approximation to the circuit's categorical mutually exclusive Pauli alternatives. It is not a semantically exact DEM for those joint channel events. B would have been the requested non-approximated alternative, but it is unavailable for these circuits under the specified conversion settings. We did not replace the channel, alter the circuit, ignore decomposition errors, or switch to a probability threshold.

Because B produces no model, the proposed comparison cannot distinguish a correlation-matching effect from the disjoint-channel approximation. Conversion success for A and successful PyMatching construction do not establish that A preserves all native channel dependencies.

**Result: BLOCKED.** Do not execute the proposed 9-million-shot follow-up under this two-family design.
