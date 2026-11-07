# Further Scaling Decision — Q-SHIFT Hybrid Residual Sprint

## Decision: NO-GO

Do not scale the current residual-CNN experiment to 10M or 60M shots. The frozen primary candidate was balanced minibatch training at 60k samples per regime/root with the confidence-gated residual policy. It produced **1,129 errors / 225,000 shots (0.501778% LER)**, exactly the same paired result as frozen PyMatching. Its paired delta was zero with five root ties, zero discordant outcomes, and no corrections selected. It fails the frozen minimum improvement of 0.0002, the four-of-five favorable-root criterion, the negative bootstrap-upper-bound criterion, and the precision criterion (precision is undefined because the gate made zero corrections).

No other frozen candidate had fewer aggregate errors than PyMatching. The lowest-error alternatives tied the baseline and had root-level confidence intervals spanning zero; all nine Holm-adjusted p-values were 1.0. Five independent roots are insufficient for confirmatory inference, so this is a development feasibility decision, not proof of equivalence.

## Operational status

The Python controller is terminal and its persisted state is `failed`; it is not running (`PID 11656` absent, no sprint lock). All 30 jobs, data partitions, predictions, and evaluations are present and pass the separate read-only evidence audit. The controller's only failure was the final verifier/status ordering described in `RUNNER_FAILURE_DIAGNOSIS.md`. Do not restart or resume training. Keep the historical `failed` status and use the external audit manifest for the verified evidence inventory.

## Independent test

Independent-test access was **0**. No independent-test files or test labels were read. The independent test remains sealed.
