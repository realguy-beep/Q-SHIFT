# Official belief-matching source audit

## Pin and license

- Repository: [oscarhiggott/BeliefMatching](https://github.com/oscarhiggott/BeliefMatching)
- Release tag: `v0.2.0` (annotated tag peeled to commit `4458c278bbec273c8c1a26411dadccc49222f8ef`)
- Installed package: `beliefmatching==0.2.0`, from the exact commit above.
- Pinned implementation module SHA-256 after LF newline normalization: `03229b09559f7059aa6bd7bd6ce80ee1190b41e702f49625ef511074ff42238f`.
- License: Apache-2.0 ([pinned LICENSE](https://github.com/oscarhiggott/BeliefMatching/blob/4458c278bbec273c8c1a26411dadccc49222f8ef/LICENSE)).
- Relevant pinned files: `setup.py`, `src/beliefmatching/belief_matching.py`, `src/beliefmatching/_version.py`, `tests/belief_matching_test.py`, and `README.md`.

The official README says to use `decompose_errors=True` when providing a DEM. Its converter parses separator-separated components, requires each component to target at most two detectors, and builds a parity-check matrix over full error-mechanism hyperedges plus a matrix for graphlike components. On BP convergence it maps the inferred mechanism vector through the observable matrix; on nonconvergence it derives edge probabilities from BP likelihood ratios and constructs a new PyMatching instance for that shot. Sources: [pinned implementation](https://github.com/oscarhiggott/BeliefMatching/blob/4458c278bbec273c8c1a26411dadccc49222f8ef/src/beliefmatching/belief_matching.py), [pinned README](https://github.com/oscarhiggott/BeliefMatching/blob/4458c278bbec273c8c1a26411dadccc49222f8ef/README.md).

## Requirements and isolated build

The pinned `setup.py` declares Stim, PyMatching >=2.0.1, LDPC, Sinter >=1.11, and NumPy <=2.2.6. The upstream CI matrix includes Python 3.9–3.13 and LDPC 0.1.60/latest on Ubuntu; this task tested only Python 3.12.10 on Windows 11.

An isolated virtual environment successfully installed the pinned editable source. Exact versions are in `requirements-ns3b.lock.txt`: Stim 1.16.0, PyMatching 2.4.0, LDPC 2.4.1, NumPy 2.2.6, SciPy 1.18.1, Sinter 1.16.0. No global packages or system tools were changed. The installed LDPC is 2.x, so upstream selected `ldpc.BpDecoder`.

The adapter fails construction unless package metadata reports version 0.2.0 and the installed `belief_matching.py` content matches the pinned implementation hash above. This prevents a different package revision from being silently recorded under the expected commit.

## Semantics and limits observed in source

- Input: `stim.Circuit` or `stim.DetectorErrorModel`; Q-SHIFT adapter uses a concrete decomposed DEM.
- Input dimensions: detector columns in Stim D0…D(n−1) order; output observable predictions in L0…L(m−1) order.
- Output: `decode_batch` returns a boolean matrix `[shots, observables]`; the Q-SHIFT adapter validates and returns contiguous `uint8` with the same shape.
- Boundary mechanisms are represented by one-detector columns and a virtual matching boundary. Q-SHIFT fixed fixtures exercise one-detector syndrome inputs.
- Multiple observables are represented by an observable parity-check matrix. Q-SHIFT has one observable; the adapter checks expected count/order and the NS-2C checked wrapper validates actual metadata/dimensions.
- DEM error probabilities are treated as independent mechanism priors. They inherit the DEM approximation and are not an exact categorical-circuit likelihood.
- The source README reports >100x slowdown relative to PyMatching v2 as a general implementation warning because the reference runs BP on each shot and rebuilds a matching object on fallback. The measurements below are Q-SHIFT d3 fixed-fixture observations, not a general guarantee.

## Scientific comparison relevance

For the Q-SHIFT bench, both BeliefMatching and the ordinary/correlation-enabled PyMatching arms consumed the same 40-detector, one-observable, 591-instruction decomposed approximate DEM. Their algorithmic handling differs, but model input and assumed DEM weights are the same. That is stronger information parity than the NS-3A prototype comparison, where BP used an undecomposed DEM and PyMatching a decomposed one. Neither representation equals the original categorical circuit distribution exactly because Stim conversion uses `approximate_disjoint_errors=True`.
