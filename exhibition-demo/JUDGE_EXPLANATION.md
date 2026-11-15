# One-minute judge explanation

“Q-SHIFT is a software demonstration of quantum error correction. A surface
code measures checks around data qubits. The changed checks are called
detectors; they give clues about faults without directly reading the encoded
logical information. A decoder uses that detector pattern to predict a logical
correction.

“In the changing-noise mode, this laptop samples a small simulated circuit with
Stim and compares PyMatching decoders on the same detector observations. One
uses a fixed nominal noise model. One estimates the burst setting from
detectors. A third, privileged reference is told the simulated true setting,
so it is an oracle and not a practical decoder.

“The separate Stage 5 research study reported a 21.86% relative LER reduction
against nominal zero-burst matching in its tested simulated conditions. It did
not establish that adaptive decoding beats a strong static burst-aware decoder
or works better on quantum hardware. Small live demo runs can tie or reverse
the aggregate result.”

The mode A lattice drawing is a teaching schematic. Its fixed DEM fixture is
deterministic and is not a sampled research shot.
