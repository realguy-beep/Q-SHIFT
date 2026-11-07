# GPU and throughput validation

## Environment

The host reports an NVIDIA GeForce RTX 4050 Laptop GPU with 6,439,305,216 bytes (6,141 MiB) VRAM, and 16,312,205,312 bytes of system memory. NVML was installed and returned live GPU, CPU and RAM values. In the saved smoke progress snapshot, GPU utilization was 0%, memory use 231,735,296 bytes (about 221 MiB), temperature 47°C and power 14.421 W; CPU use was 50%, system RAM use was 11.43 GB (70.1%), and the worker process RSS was 405,692,416 bytes. These are snapshots, not peaks.

PyTorch was installed as `2.15.0+cpu`, so `torch.cuda.is_available()` returned false and the model trained on CPU. The initial CUDA 12.8 PyTorch install timed out after approximately 0.5 GB of the 2.75 GB wheel (`ReadTimeoutError` from `download-r2.pytorch.org`, initially at roughly 345 kB/s). A force-reinstall retry with a 300-second read timeout stayed in the download phase for about six minutes without a completion signal and was canceled before installation; the existing CPU build remained installed. Therefore this report contains **no GPU training throughput or CUDA inference benchmark**. NVML telemetry was real; the reported 0% GPU use is consistent with CPU training.

## Bounded smoke measurements

Run `69e013ce457946f28f0ceb6308f39647`, balanced Z memory, d=3, five rounds; 8,000 train / 1,000 validation / 1,000 test shots. One stream pass trained both small MLPs. The worker reported 4,282.1 unique training shots/s over 1.868 s; its training-plus-test interval was 1.961 s. SQLite run creation to terminal status took about 18.20 s, including process startup, model/circuit construction and validation sampling outside the worker's throughput clock.

Measured test-stage CPU timings for 1,000 shots:

| Operation | Time |
|---|---:|
| Stim test sample generation | 0.571 ms |
| PyMatching test decode | 0.886 ms |
| Direct MLP inference | 0.568 ms |
| Residual MLP inference | 0.386 ms |

These are single-batch timings from this machine and software build. They are not stable benchmark estimates; model/circuit startup is excluded from inference timing. No VRAM was allocated by PyTorch.

## Paired smoke outcomes

| Scorer | Errors / 1,000 | LER | Wilson 95% interval |
|---|---:|---:|---:|
| No correction (identity prediction) | 52 | 5.2% | 3.987–6.756% |
| Frozen Phase 2B PyMatching | 4 | 0.4% | 0.156–1.024% |
| Direct MLP | 52 | 5.2% | 3.987–6.756% |
| PyMatching + learned residual | 4 | 0.4% | 0.156–1.024% |

Direct MLP versus matching: 50 shots were wrong only under the MLP and 2 only under matching, a net +48 errors (+4.8 percentage points); the exact paired two-sided McNemar value is 6.12×10⁻¹³ for this one sample. The residual model had 0 candidate-only and 0 matching-only errors and 0 prediction disagreements: it made the same corrections as matching on these 1,000 shots. The direct model's 52 errors equal the identity count, but the direct predictions need not equal identity predictions on every shot.

This is a pipeline smoke result, not evidence about generalization, GPU performance, decoder superiority, or adaptive Q-SHIFT. Do not infer population significance from its shot-level interval or p-value.
