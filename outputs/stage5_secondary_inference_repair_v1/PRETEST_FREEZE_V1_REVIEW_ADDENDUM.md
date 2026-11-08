# Addendum: clarification of the v1 pre-test freeze rejection

This addendum corrects one sentence in PRETEST_FREEZE_V1_BLOCKED.md without changing that frozen historical note or the v1 freeze.

An independent check after the v1 preflight rejection verified all 45 hashes listed in STAGE5_PRETEST_FREEZE.json. The freeze was rejected solely because its status value, PRETEST_FROZEN_NOT_AUTHORIZED, did not match the v1 runner's required READY_NOT_AUTHORIZED_TO_SAMPLE value. The runner stopped before circuit construction or sampling. The v1 freeze source hashes were intact; the earlier note's statement that the builder hash no longer verified was inaccurate.

The v2 freeze, runner, auditor and preflight are separate files. The v1 freeze and note remain preserved as historical evidence. Stage 5 shots generated: zero.
