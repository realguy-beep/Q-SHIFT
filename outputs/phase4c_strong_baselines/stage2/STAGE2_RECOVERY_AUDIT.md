# Stage 2 checkpoint recovery audit

All 60 checkpoints passed filename/root, shape, binary observable/prediction, decoder index, and exact re-decoding under the five frozen DEMs. Packed detector bytes were correctly unpacked to 40 binary columns; prior rejection incorrectly checked packed bytes for binary values. Original checkpoint hashes are recorded in recovered JSON. Calibration arrays and fitting score records are absent, so calibration selection cannot be independently refit; saved choice indices and test predictions were verified. No new simulation was run during recovery.

Aggregate checks against every per-root row passed; recovered reporting CSVs were generated directly from the verified JSON.
