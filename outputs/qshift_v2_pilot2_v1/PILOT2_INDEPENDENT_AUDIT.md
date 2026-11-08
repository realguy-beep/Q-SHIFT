# Q-SHIFT v2 Pilot 2 independent audit

Status: **PASS**. This audit is separate from the runner and analysis implementation.

## Checks

- PASS — seed disjointness
- PASS — seed inventory hash
- PASS — shot budget
- PASS — correlation flags explicit at build and decode
- PASS — dem and matcher construction flags
- PASS — chronological controller boundary
- PASS — paired array shape
- PASS — warmup excluded
- PASS — all predictions binary
- PASS — result row count
- PASS — metric denominators and ler
- PASS — paired outcome alignment and discordances
- PASS — graph switch counts
- PASS — computational instrumentation and total cpu
- PASS — final source hashes
- PASS — config reproducibility
- PASS — results hash
- PASS — paired hash
- PASS — tuning selection rule and denominators
- PASS — selected tuning candidate
- PASS — no stage5 or sealed access asserted
- PASS — statistics finite

Seed audit: 932 new sampler seeds; 5108 historical values; 0 collisions. Shot total: 298,500.

Paired archive: [160, 2, 8, 1300] predictions, 2,560 stream-policy-mode rows. Warm-up: 200; scored per stream: 1300.

The bootstrap was independently recomputed from aligned shot outcomes with streams as the resampling unit. No Stage 5 files or sealed outcomes were opened.
