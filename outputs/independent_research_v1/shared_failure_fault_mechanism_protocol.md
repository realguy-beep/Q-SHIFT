# Two-qubit fault composition in shared decoder failures

## Hypothesis

The ratio5/10 matchers share most failures. A bounded circuit-level fault-composition screen may show whether shared failures involve more two-qubit pair faults or particular Pauli-pair classes than failures corrected by one matcher. This is descriptive mechanism work, not a decoder proposal.

## Fixed design

- Use actual ratio10, p_gate=p_measure=.003, the high-LER mismatched-basis cells only: X-biased/Z-memory and Z-biased/X-memory, at d3/5 rounds5 and d5/9 rounds (four cells).
- Instrument every `PAULI_CHANNEL_2` location as a mutually exclusive categorical branch with four private outcome flags, using the previously validated `categorical_importance_sampler.instrument_circuit(alpha=1)` implementation. Preserve all one-qubit channels and measurement flips. Verify detector/logical dimensions and compare instrumented versus original circuit LER in a 5,000-shot independent preflight per cell; stop if any absolute standardized difference exceeds four.
- Preflight seeds: instrumented 2026112601–2604, original 2026112611–2614. Main seeds: 2026112621–2624. Main uses 100,000 instrumented direct samples/cell only if all preflight checks pass and projected time is <=5 minutes.
- Decode each syndrome with the frozen assumed-ratio5 and ratio10 matchers. Summarize each pair-fault count and Pauli-pair composition among both-correct, both-wrong, ratio10-fixes-ratio5, and ratio10-breaks-ratio5 groups. Include the number of shots in each group and note that one-qubit/measurement faults are not instrumented.
- No post-hoc decoder changes. This one synthetic channel screen cannot identify causal fault mechanisms or generalize to hardware.
