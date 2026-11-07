# Exact reference validation

## What was validated

`categorical_reference.py` exhaustively enumerates each toy's Cartesian product, selecting one outcome per categorical location and accumulating `P(syndrome, L0)`. A second route in `toy_circuits.py` independently forces each selected outcome through a Stim circuit by replacing each non-identity channel draw with a one-hot categorical channel. For every configuration it samples the resulting deterministic circuit once, checks the observed detector and observable bits against the separately derived parity-mask mapping, and accumulates probability mass using the configuration probability.

The two routes agree for all 64 one-qubit configurations and all 256 two-qubit configurations, including the full joint distribution. The total accumulated mass is 0.9999999999999994 and 0.9999999999999996, respectively, from floating-point arithmetic. All 320 forced-outcome Stim checks are deterministic checks, not Monte Carlo evaluation or Phase 2B test shots.

Tests also verify identity inclusion, normalization, configuration cardinality, one outcome per location, invalid-mass rejection, deterministic tie resolution, and the key approximate-matching comparison. The two-qubit exact posterior has tied syndromes 1 and 2; the declared `1e-15` tie tolerance maps both to logical bit 0.

## Reproduce and result

From this directory run:

```powershell
python -m py_compile categorical_reference.py toy_circuits.py run_toy_comparisons.py test_categorical_reference.py
python -m unittest -v
python run_toy_comparisons.py
```

The recorded run used Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3, and Python 3.12.10. All eight unit tests passed; the comparison runner exited successfully. `TOY_RESULTS.json` records `stochastic_shots_generated: 0`. The 320 forced-outcome calls are explicitly counted separately.

These checks validate the toy's categorical semantics and exact posterior computation. They do not establish that the Phase 2B Stim-to-DEM approximation preserves categorical channel likelihoods.

