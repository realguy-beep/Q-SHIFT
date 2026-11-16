# Preregistered replay
Before reading archived predictions: select the first 50 detector rows from roots 00, 07 and 19 for each of known/hidden and q indices 0, 1 and 2: 18 archives, 900 unique shots. Replay all six frozen arms. Archived predictions are read only after all predictions for that archive are computed. Verify frozen source hashes, execution identity, manifest, archive hashes and model metadata before decoder construction. No labels, sampler or sealed files. Stop on any mismatch. 900-second hard subprocess timeout; no retry. Independent orchestration uses frozen decoder implementation, not independent decoder code.

◐ Source and archive verification
☐ Deterministic subset and replay
☐ Results and limitations
