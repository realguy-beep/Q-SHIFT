# Q-SHIFT: An Adaptive Quantum Error-Correction Framework for Nonstationary Noise

**PROJECT SUMMARY**  |  **SIMULATION-BASED RESEARCH PROTOTYPE**

## Problem and objective

Quantum computers hold information in delicate physical states. Small faults can change a calculation, and fault conditions can shift over time. A decoder uses measured error signals to infer likely faults. A fixed decoder uses one model throughout, which may not suit changing noise. Q-SHIFT asks whether detector measurements can reveal change early enough to choose a more suitable method. The hypothesis is that careful selection might reduce errors compared with a strong fixed method. The goal is not only to name a noise condition, but to see whether it changes which correction works best.

## System built

Stim simulates a distance-3 rotated surface-code memory over five rounds; PyMatching decodes its detector signals. The prototype varies gate and measurement noise and builds nine matching models with different assumed noise strengths. A sliding-window estimator and controller can use completed earlier blocks to choose a model for the next block, while retaining a fixed-decoder fallback. Comparisons use the same simulated shots and observable labels.

## Evidence and findings

The project built reproducible simulation, calibration, decoder-bank, and paired-evaluation workflows. Under measurement-heavy noise, static calibration reduced errors from 1,118 to 940 in Phase 4A and from 1,165 to 1,008 in Phase 4B, each on 600,000 shots against a nominal fixed model. A broader 1.8-million-shot Phase 4C test compared calibration with a stronger pooled fixed model across three regimes. Its equal-regime difference was +0.0000156 (95% CI -0.0000489 to +0.0000767; p=0.667), so an overall improvement was not established. Exploratory adaptive development also did not show a reliable advantage.

## Potential and conclusion

A future hardware version could monitor live syndrome measurements as conditions drift. It would need real-time readout access, device-specific calibration, reliable timing, and processor integration; none is demonstrated here. If later validated, adaptation could help preserve information during longer quantum computations. Such a controller would sit beside the processor, analyze its readouts, and return choices for later cycles. Q-SHIFT is a research prototype and a platform for testing this possibility, not evidence of improved quantum hardware.

**Evidence note.** All results are simulated. Phase 4C test predictions were independently re-decoded, but calibration shots were not saved; adaptive evidence is exploratory.