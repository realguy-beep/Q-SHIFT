# Failed attempt 1 (preserved)

On 2026-11-08, the first Pilot 2 runner execution stopped in the controller-tuning summary before any evaluation streams were generated or decoded. It raised `TypeError` while averaging a `None` detection delay for smooth drift, which has no discrete change point.

The deterministic profile templates (5,000 shots), static-selection set (5,500), stationary GLR-calibration set (36,000) and change-detection tuning set (12,000) were generated from the frozen Pilot 2 seed inventory: 58,500 unique development shots. Their arrays were held in process memory and not saved. They are exactly reproducible from the recorded configuration and seeds; the corrected run regenerates the same samples, so these are reused observations, not fresh shots. No evaluation stream or sealed/Stage 5 material was accessed. No Pilot 2 result file was written by this failed attempt.

Correction: controller-delay tuning now averages only step-up, step-down and transient roots with discrete change points. Smooth-drift roots remain in the fixed tuning budget and receive no single-point delay statistic. This rule is now explicit in the frozen protocol. The failure and correction are retained here.
