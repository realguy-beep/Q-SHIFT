# Google qsim feasibility

## Finding

qsim is a Cirq-compatible **state-vector quantum circuit simulator**, not a QEC decoder or a faster replacement for Stim's stabilizer/DEM workflow. The upstream interface documents full-state-vector simulation, measurement sampling and intermediate measurements; qsimcirq also routes noisy circuits through a trajectory simulator when the circuit requires trajectories. A Cirq noise model may therefore support a future independent trajectory-based cross-check if every Q-SHIFT gate, channel, measurement, reset, feedback operation and detector parity is faithfully translated.

## Potential value

- Independent implementation can catch errors in a custom circuit renderer or measurement-to-detector conversion.
- A small non-Clifford/noisy circuit may be checked when an independent state-vector/trajectory calculation is scientifically necessary.
- Cirq has noise-model abstractions and qsim's trajectory path can handle some noisy simulation workflows.

## Limits for this project

- Q-SHIFT's current circuit is Clifford with Pauli categorical channels and repeated measurements; Stim is the natural efficient engine for stabilizer sampling and DEM construction. qsim does not provide a decoder or validate PyMatching's inference.
- A literal state vector scales exponentially. The current distance-3 memory circuit has about 25 data+measurement qubits, while proposed Q-SHIFT studies require many repeated shots; intermediate measurements require repeated trajectory runs. This is unlikely to improve throughput over Stim.
- qsim's gate set/noise operation translation must be checked for the exact custom correlated burst and all reset/measurement semantics. A translated trajectory ensemble is not a deterministic equivalence proof; matching detector distributions needs a separately designed statistical validation, which is not authorized here.
- qsim will not repair approximation in a Stim DEM or establish decoder optimality. Non-Pauli channel support is mediated by Cirq/noise trajectory compatibility; do not assume every channel is accepted by the qsim translator.

## Recommendation

Do not install or migrate to qsim now. Keep Stim for the Q-SHIFT pipeline. Consider a small, separately approved qsim/Cirq cross-simulator only if the research adds a genuinely non-Clifford/non-Pauli mechanism or a circuit-construction check that Stim cannot independently settle. First verify translator support and compare a handful of deterministic circuit semantics (qubit order, detector parity, observables) before any stochastic cross-engine comparison.

Sources: [qsim upstream](https://github.com/quantumlib/qsim), [Cirq interface documentation](https://github.com/quantumlib/qsim/blob/main/docs/cirq_interface.md), [qsim simulator implementation](https://github.com/quantumlib/qsim/blob/main/qsimcirq/qsim_simulator.py), [Stim paper](https://arxiv.org/abs/2103.02202).
