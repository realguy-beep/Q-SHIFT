# Pre-test freeze candidate v1: blocked and superseded

`STAGE5_PRETEST_FREEZE.json` was created as an initial candidate but was not used for any sampling. The runner's fail-closed state check requires `READY_NOT_AUTHORIZED_TO_SAMPLE`, while the candidate recorded `PRETEST_FROZEN_NOT_AUTHORIZED`; therefore the no-sampling preflight correctly stopped immediately. The freeze-builder source was subsequently repaired, so the original hash set also no longer verifies against the current builder file. No Stage 5 shots were generated during this failed attempt.

The original candidate JSON and its companion v1 runner files are preserved. They are not active. The v2 amendment, runner, auditor, freeze and no-sampling preflight are separate files and are the only candidate for readiness review.
