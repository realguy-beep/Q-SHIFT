# Round-wise gate-rate heterogeneity: development result

## Result

The exact profile-specific graph had fewer logical failures than the pooled same-mean graph in both temporal phases. At phase A, rates across rounds were 0.00075, 0.00525, 0.003, 0.00075, 0.00525: 1,655/200,000 failures versus 1,709/200,000 for pooled matching, a paired delta of -0.000270 (95% CI [-0.000450, -0.000090], exact McNemar p=.0039). At phase B, failures were 1,474 versus 1,512, delta -0.000190 (95% CI [-0.000349, -0.000031], p=.0226). The equal-weight macro relative reduction was 2.84%, below the preregistered 10% advancement threshold.

The profile decoder used 1.04x and 1.02x pooled decode time for phases A and B. Neither profile was harmed, but the effect size is small. This supports a limited claim: given a known, repeating round-rate map in this simulator, exact per-round matching weights help slightly over the same-mean stationary weights. It does not support online adaptation. Calibration and change-detection costs would further reduce utility.

## Validity and limits

Both profiles changed only two-qubit channel rates, retaining a 1:1 average probability factor, the same 120 pair sites, five rounds, 26 qubits, 40 detectors, one observable, one-qubit rates, measurement rates, and pairwise Pauli composition. Both use the same approximate-disjoint DEM threshold .01. The 400,000 main samples used independent seeds; 400 additional preflight samples were used for integrity/runtime checks. No confirmatory or sealed data were accessed.

This is a synthetic d3 stress test, uses the true temporal map as decoder input, and applies a deliberately patterned round-wise rate sequence. The DEM remains an approximation for categorical pair noise. It is not a hardware estimate, drift detector, threshold result, or evidence toward a 10,000-fold reduction.

Artifacts: `temporal_rate_hotspot_protocol.md`, `temporal_rate_hotspot.py`, `temporal_rate_hotspot_results.json`.
