# Phase 4B frozen independent replication

Fresh 20 roots 52000001..52200001 step 10000. One primary condition: gate=.001, measurement=.006. Each root has independent calibration 20k, validation 10k, paired final test 30k. Fixed DEM (.003,.003); calibrated decoder chooses from original 3x3 grid using the same detector marginal Jeffreys profiles/composite Bernoulli score. Reuse Phase 4A template bank (`TEMPLATES.json`), so this replicates calibration/test roots and inference while sharing finite templates; it is not an independent template-bank replication. Primary success unchanged: absolute gain >=.0001, exact McNemar p<.05, seed bootstrap upper CI<0. Calibration >=16/20 exact recovery and validation >=100 disagreements plus lower residuals to proceed. Freeze before test. No test-based tuning.

Implementation details are inherited verbatim from Phase 4A method: eb31c830a580c8cdd2744e45fe143c35074cf0bfe59eaeccfd76cc4ecf7705a1. Native Stim rotated Z-memory d3 r5 channels.
