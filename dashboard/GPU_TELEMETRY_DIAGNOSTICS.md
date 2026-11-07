# Q-SHIFT GPU telemetry repair record

## Diagnosis

The live service previously answering `http://127.0.0.1:8765/api/health` returned `gpu.available=false`, `source="NVML unavailable"`, and `unavailable_reason="Unknown Error"`, while reporting `cuda_available=true`. Its response had no Python executable, PyTorch version, device name, or traceback fields. The old `telemetry.py` wrapped NVML handle, memory, and utilization reads in one exception boundary and returned immediately on any NVML failure, so it did not use the working `nvidia-smi` fallback. This turned one provider/metric failure into “all GPU telemetry unavailable.”

The old process did not persist a traceback, and its exact NVML exception type and failing call cannot be reconstructed from the returned string. The process already bound port 8765 (`WinError 10048` when a fresh server tried to bind it); its PID was not visible to the managed shell, so it could not be safely restarted in place. The updated source was verified in a fresh Python process and through FastAPI's in-process test client. Restart the existing dashboard using `python dashboard/run_local.py` to load the repaired code.

## Independent provider checks

Environment: `C:\Users\LENOVO\AppData\Local\Programs\Python\Python312\python.exe`; PyTorch `2.14.1+cu126`; CUDA runtime `12.6`; `torch.cuda.is_available() == True`; one NVIDIA GeForce RTX 4050 Laptop GPU.

`nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader,nounits` returned:

```text
NVIDIA GeForce RTX 4050 Laptop GPU, 0, 0, 6141, 46, 9.48
```

Direct NVML initialization and calls succeeded for name, utilization, memory, temperature, and power. A sample returned 0% GPU utilization, 231,735,296 / 6,439,305,216 bytes VRAM, 45°C, and 9.160 W. Values are live snapshots and naturally vary.

The repaired telemetry implementation was also exercised through `/api/health` using FastAPI's test client: CUDA true, same Python executable, PyTorch CUDA version `12.6`, GPU source `NVML`, and non-null readings for all five requested metrics. The fallback path and traceback logger are regression-tested with simulated NVML errors; those simulated errors are written to in-memory test loggers, not production logs.

## Backend and worker environment

`WorkerManager.start()` launches the worker with `sys.executable`. The repaired health response and the completed smoke run both recorded `C:\Users\LENOVO\AppData\Local\Programs\Python\Python312\python.exe`. The worker metadata reports the same Python 3.12.10 and PyTorch `2.14.1+cu126` build as the dashboard process.

`CUDA READY` is driven by `torch.cuda.is_available()` in `device_snapshot()`. Run-level device reporting is separate: the worker marks CUDA training verified only after CUDA-resident training tensors and model parameters complete a forward/backward/optimizer step and `torch.cuda.synchronize()` succeeds. The UI labels saved runs with their actual execution device; the prior CPU-only run is shown as “Historical CPU run.”

## Fresh 10K smoke run

- Run ID: `18ca68def80946838b26aaea7f59ff3e`
- Seed root: `1900000001`; screened against 2,076 recoverable historical seed values, with no collision.
- Samples: 8,000 train + 1,000 validation + 1,000 test.
- Device: `cuda`, NVIDIA GeForce RTX 4050 Laptop GPU; `cuda_training_verified=true`; mixed precision enabled.
- CUDA peak allocated/reserved: 18,887,680 / 23,068,672 bytes.
- Saved-test results (descriptive smoke only): identity 53/1,000; PyMatching 3/1,000; direct MLP 53/1,000; PyMatching plus neural residual 3/1,000.
- `verify_run.py` independently passed: hashes, seed partition, circuit/DEM, saved predictions, model checkpoint rescoring, and paired metrics.

The earlier CPU-only run `69e013ce457946f28f0ceb6308f39647` remains intact. Its metadata says device `cpu`, CUDA unavailable, and PyTorch `2.15.0+cpu`; the API run list now labels it “Historical CPU run.”

## Validation and browser access

`python -m unittest discover -s dashboard\\tests -v`: 15 tests passed. `node --check dashboard\\static\\app.js` and `python -m compileall -q dashboard` passed. `python dashboard\\verify_run.py dashboard\\run_data\\runs\\18ca68def80946838b26aaea7f59ff3e` returned `PASS`.

The updated server could start on port 8766, but Codex's in-app browser timed out connecting to `127.0.0.1:8766`. Direct local Python API testing succeeded. Browser rendering therefore remains unverified in this session; restart the dashboard in the user's local shell and reload the page after the server is replaced.
