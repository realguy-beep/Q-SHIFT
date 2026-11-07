# Q-SHIFT Stage 4 — Competition Evidence Summary

Q-SHIFT tested whether it could estimate the strength of a synthetic correlated error from detector measurements and rebuild a conventional PyMatching decoder. It ran a distance-3, five-round simulated surface-code memory experiment. Each test batch was decoded by the same fixed decoder, the detector-estimated decoder, and a reference decoder given the true simulated probability.

The study used 175,500 new simulated shots across five burst probabilities and seven independent roots per probability. The adaptive estimate used detector-only calibration data; test outcomes were used only to score predictions. An independent audit rebuilt the decoders and reproduced every saved prediction. No quantum hardware was used and the independent test set remained sealed.

Across the four nonzero burst conditions, the detector-estimated decoder changed logical error by -0.164286% on average versus fixed nominal PyMatching (95% root-cluster interval [-0.197143%, -0.132857%]). The prespecified development gate was **PASS**. This result is limited to the chosen synthetic burst model and should not be described as a hardware improvement or general adaptive-decoding advantage.

Full counts, uncertainty, methods, and limitations are in `STAGE4_RESULTS.md` and `STAGE4_INDEPENDENT_AUDIT.md`.
