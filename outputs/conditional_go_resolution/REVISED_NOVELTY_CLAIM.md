# Revised novelty claim

## Claim rejected

Q-SHIFT cannot credibly claim as novel the general idea of estimating noise from causal syndrome history and updating a matching decoder while noise changes. This is already present in the adaptive weight estimator of Spitz et al. (2018), the real-time Gaussian-process estimator of Huo and Li (2017), syndrome-history DEM reconstruction in Bhardwaj et al. (2026), and matching-history reweighting in the DGR preprint. The 2026 Sivak et al. work additionally demonstrates detector-driven adaptation of physical controls on hardware and prior-based decoder steering from previous evaluation data. A comparison of these methods under stricter common-resource controls may still be useful, but by itself is not a new adaptive algorithm.

## Candidate research pivot (not novelty-verified)

If the project is redesigned, the materially different question is:

> **For a fixed circuit-level QEC measurement process, when can causal detector histories identify the decoder-relevant posterior well enough to choose between recoveries, and when do physically different noise processes remain observationally equivalent to the detector stream while implying different optimal corrections?**

This is an information/identifiability question, not a proposal to keep adjusting matching weights. A useful result could be a constructive pair of noise processes with indistinguishable detector-history distributions at a stated sample size but different optimal logical recovery, plus a characterization of what additional observable/telemetry breaks the ambiguity. The analysis would separate physical-parameter identifiability from **decoder-utility identifiability**.

This pivot is only a candidate. Syndrome-based parameter identifiability, exact edge reconstruction, DEM reconstruction and experiment-informed decoder calibration already have literature. Before authorizing it, conduct a new targeted review of those works, define a formal equivalence metric and establish that the circuit-level posterior question is not already solved. No new novelty claim is made here.

## Development evidence relevant to the pivot

The small detector-profile pilot selected the exact three grid points on all 24 calibration roots (8 per regime), but this did not guarantee better decoding. Against the frozen Stage-1 pooled point, the finite-bank model selected only 9 fewer errors over 98,304 common evaluation shots. The paired seed-stratified interval was **[-0.000417, +0.000234]** for the equal-regime LER difference, included zero, and the net reduction was about **1.32%**, below the previously proposed 5% relative / 0.0001 absolute headroom thresholds. Data-heavy evaluation was worse under the selected decoder. This is consistent with the distinction between learning parameters and learning information that changes the logical decision.
