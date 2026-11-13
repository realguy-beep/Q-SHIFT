# Deterministic decoder correctness results

Run in Python 3.12.10 from this directory:

```powershell
python -m unittest -v test_decoder_prototypes
```

**Final result: 22 tests passed in 0.251 seconds.** The test suite covers syndrome/observable convention, detector order, output shape/type, boundary and logical mechanisms, two-detector hyperedges, multiple and duplicate mechanisms, parity cancellation, DEM target and probability parsing, exact ties, p=0/1 and impossible syndromes, oracle state cap, an independent Fraction-based exact MAP reference, tree BP/MAP agreement, BP nonconvergence handling, extreme-probability numerical finiteness, malformed inputs, repeatability, and input immutability.

One earlier test attempt failed because the test's expected canonical detector parity was wrong: `(0,0,1,1,1)` reduces to `(1,)`. The test expectation was corrected; the complete suite subsequently passed. This failure is preserved here rather than omitted.

The tests establish software behavior on small deterministic fixtures. They do not establish Q-SHIFT logical error rate, loopy-BP optimality, stochastic performance, or full-scale scientific improvement.
