# Novelty assessment of the three candidate contributions

## A. Limits of regime-aware decoder switching

**Possible contribution.** Show that accurate detector-based regime recognition does not necessarily create useful decoder choices: calibration uncertainty, weak candidate utility differences and switching delay can erase apparent opportunity.

**Prior work and novelty.** Noise-aware adaptation is established. Darmawan (2025) quantifies parameter sensitivity for near-optimal tensor-network decoding; the 2025 Local Clustering Decoder changes graph properties in hardware using runtime control signals. “Classify and switch” is not novel by itself. A possible distinction is a benchmark of whether a practical calibration-selected PyMatching bank has enough utility headroom to justify causal switching.

**Current support.** Phase 1 recognition was 94.4%, but its validated lookup policy made no switches. Phases 2A/2B found no calibration-selected regime differences. Phase 4C found no improvement over pooled fixed. Phase 5 adaptive often tied fallback. This supports “no gain has been established in tested settings,” not “switching cannot help.”

**Required work and risk.** There is no single frozen, adequately powered adaptive test over multiple distances and dynamic schedules. Phase 5 is development-scale and Stage 2 lacks calibration arrays. Needed: stable calibration headroom, causal transition schedules, calibrated estimator confidence, delay/false-switch metrics and fresh multi-distance tests. Publication risk is high unless framed as a careful benchmark/negative-result study; universal limits are unsupported.

## B. Basis-dependent decoder selection under Pauli bias

**Possible contribution.** At fixed total local gate-fault probability, Phase 2B selected one model for X-memory and another for Z-memory, but not different models by generating composition.

**Prior work and novelty.** Biased-noise code tailoring is well established; ordinary basis-sensitive matching is expected and is not by itself novel. Phase 2B has six basis/composition cells, 20 test roots/cell and 1.2 million shots; regime-informed selection tied the global model at 5,532 errors.

**Required work and risk.** Test both memories at d=3,5,7, vary X/Y/Z ratios at fixed total fault probability, separate readout and data noise, use native categorical two-qubit channels where appropriate, and report root-level uncertainty and multiplicity control. Compare code tailoring and model-weight tailoring. Risk remains medium-to-high because prior work directly studies bias tailoring; novelty would need a full calibrated mapping or new physical model, not simply basis dependence.

## C. DEM/PyMatching versus sample-trained posterior surrogates

**Possible contribution.** Determine whether DEM simplification changes logical decisions compared with a faithful channel-likelihood model.

**Prior work and novelty.** The question matters because categorical Pauli channels can carry correlations not represented exactly by an independent-mechanism DEM, and learned/near-ML decoders are established. Phase 2C does not provide a meaningful likelihood benchmark: its selected random forest made 2,579 errors versus PyMatching's 628 on 120,000 shots. It did not calculate exact P(logical observable | detector) or bound posterior error. It only shows that this forest was weaker.

**Required work and risk.** Validate a reference on analytically/exhaustively tractable circuits, quantify likelihood approximation error, compare both memory bases and several distances on independent calibration/test sets, and separate posterior proper scores from LER. Exactness must be limited to proved assumptions. Risk is high until a trustworthy reference exists.

## Recommendation

Use **A as the umbrella question**, narrowed to: *When does a calibrated decoder bank have enough headroom for causal switching to beat the strongest fixed baseline?* Use basis dependence as a controlled factor, not the main novelty claim. Defer C until a validated near-ML or channel-likelihood reference exists. The current work is a substantial pilot and motivation, not a completed novel paper.
