# Blockwise temporal pattern across two d3 tasks: aggregate gate failed

## Design

The frozen blockwise per-round gate-rate pattern and reversal were applied to Z-memory/X-biased and X-memory/Z-biased d3 circuits. Each task used its own stationary nominal selector and matchers. Two-qubit rate factors were [.25,.25,1.75,1.75,1]; average rate, one-qubit/measurement probabilities, Pauli composition, and geometry were unchanged. This is task transfer using task-specific models, not cross-basis model transfer.

## Result

Across four equal-weight task/profile cells, macro LER was .0094445 for nominal correlated matching and .008718 for the selector, a 7.69% reduction. Full inference cost was 1.396x. The frozen 10% macro gate failed, so no independent replication was launched.

The benefit was strongly task-dependent. Z-memory/X-biased cells improved 13.14% and 13.80%. X-memory/Z-biased cells improved only 0.71% and 3.07%; the first paired interval crossed parity, the second showed a small difference. Thus the first task reproduces the earlier ~12% temporal gain, but it does not carry across the complementary task at the same utility threshold.

A first script attempt stopped before sampling because the task/profile iterator lengths did not match; the setup was corrected and the experiment rerun. That failed attempt generated no samples. The corrected run used 40k preflight and 2M main samples.

## Interpretation

Keep temporal selector claims limited to Z-memory/X-bias d3 and the two tested rate shapes. The complementary X-memory/Z-bias task is near-neutral, and the aggregate fails the frozen gate. Do not generalize to both logical tasks or online adaptation. No confirmatory or sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_temporal_two_task.py
```


## Run metadata

Run used the reproduction command from base revision `8e63b41`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. The JSON records runner, protocol, and temporal-builder-reference SHA-256 hashes. Peak RSS was not captured.
