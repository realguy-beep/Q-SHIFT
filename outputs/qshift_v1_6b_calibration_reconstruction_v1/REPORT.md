# V1.6b calibration reconstruction

All 340 comparisons passed without mismatch (absolute tolerance 1e-10, likelihood 1e-8) in 39.797 seconds. Verified 38 frozen source files, 300 archive hashes and sizes, run-manifest and execution identities, installed versions and 900-shot replay summary. No sampling, evaluation labels or sealed data were accessed.

The independently written parity arithmetic reconstructed both device classes, all class scores and device rate estimates, and the learned/true-class rate estimates for all 144 roots. Logical flips and likelihood ratios were reconstructed from labeled device calibration using the frozen exact decoder. Class signatures, base DEM, circuit builder and exact decoder are shared frozen components; this is independent orchestration and arithmetic, not a separate decoder implementation.

Metadata SHA-256, computed on the current local bytes:

| Condition | device_learning.json | models_frozen.json |
|---|---|---|
| known | 848173f0ee9e1701147c18c6ebb8fa973836c7e116c27d6a6232f27985cc0c7c | ceeeffcf12cd0af0a7c6658525f8df07a2d696c2a940388e5bc7fdef5eead03c |
| hidden | b9e7dd78353f70d82e4f87f17559bc715e69b309f41fe6a39634b7bc9d9683bb | a7a7cb732fa640e3b1de15ca7c763054fe9f451cd240de8a2e5217d7b1d58bd0 |

These metadata files were not separately hashed in the original archive manifest. Reconstructed values corroborate their contents; newly computed hashes cannot prove their original historical bytes. The prior 900-shot replay and this reconstruction are separate from frozen directories. Full decoder replay was not performed.

Command: `py -3.12 outputs/qshift_v1_6b_calibration_reconstruction_v1/reconstruct.py` from repository root. It writes its output JSON; use a separately versioned copy/destination to reproduce without overwriting this evidence. Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3, and psutil 7.2.2 matched the recorded environment. Complete comparison data is in reconstruction_results.json.

A larger replay is scientifically justified if separately authorized, using process-tree deadline supervision; an independently implemented decoder would provide stronger assurance.