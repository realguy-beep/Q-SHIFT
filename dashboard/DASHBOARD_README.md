# Q-SHIFT training dashboard

The dashboard is a local research workbench for training small static neural decoders against a frozen Phase 2B Stim/PyMatching baseline. It does not implement adaptive noise-regime switching, does not connect to quantum hardware, and does not claim that neural decoding improves Q-SHIFT.

## Start on Windows

From the repository root, create/activate a Python 3.12 environment if desired, then install the dashboard dependencies and choose the PyTorch wheel separately:

```powershell
python -m pip install -r dashboard\requirements.txt
# CPU-only PyTorch:
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
# CUDA 12.8 build (large download; confirm driver compatibility first):
python -m pip install torch --index-url https://download.pytorch.org/whl/cu128
python dashboard\run_local.py
```

Open `http://127.0.0.1:8765`. The service binds only to loopback. `Auto` selects CUDA only when the installed PyTorch wheel reports CUDA available; otherwise the run uses CPU. The NVIDIA panel reads actual NVML or `nvidia-smi` telemetry independently of the training device.

The repository environment used for the smoke test had Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, PyTorch 2.15.0+cpu, FastAPI 0.162.0 and Uvicorn 0.54.0. The initial CUDA 12.8 PyTorch download timed out after about 0.5 GB of a 2.75 GB wheel; a longer-timeout retry was canceled after six minutes without completion. CUDA training is therefore not verified in this run.

## Controls and resource safeguards

- The selected smoke preset generates 8,000 train, 1,000 validation and 1,000 held-out test shots (10,000 total).
- Budgets above 10,000 training shots require an explicit in-dashboard confirmation. The 100M and 1B presets require two confirmations. No large run starts automatically.
- Distance 3, five rounds, the 40-detector/one-observable circuit and the Phase 2B decoder selection are locked. Noise probabilities, memory basis, batch size, learning rate and model selection are configurable.
- The backend accepts no shell command or file path from the browser. Pause, stop and checkpoint requests take effect at a mini-batch boundary; checkpoints are written atomically.
- One queued or running dashboard run is allowed at a time. Run metadata and bounded metric history are stored in `dashboard/run_data/qshift_dashboard.sqlite3`.

## Smoke-test evidence

Run `python dashboard\run_smoke.py --seed <fresh-seed-root>` to execute a bounded smoke through the same start handler, seed checks, SQLite store, manager and worker. Use a fresh root; the default seed was consumed by the saved smoke and will be rejected on rerun. The saved run is `dashboard/run_data/runs/69e013ce457946f28f0ceb6308f39647/`. Recheck it without generating samples:

```powershell
python dashboard\verify_run.py dashboard\run_data\runs\69e013ce457946f28f0ceb6308f39647
python -m unittest discover -s dashboard\tests -v
```

If a CUDA-enabled PyTorch wheel is installed, `python dashboard\benchmark_saved_inference.py dashboard\run_data\runs\69e013ce457946f28f0ceb6308f39647` measures inference on the already-saved detector features only. It reads no observable labels and generates no additional samples.

The saved evidence contains only this 1,000-shot final test batch and a 1,000-shot validation batch; training samples are streamed and not retained. `verify_run.py` re-decodes both batches, recomputes neural predictions from the saved checkpoint, checks hashes and paired metrics, and records its result plus a manifest. Results and limitations are detailed in `GPU_BENCHMARK.md` and `EXPERIMENT_PROTOCOL.md`.

## Current scientific status

The strongest saved comparison in this smoke is the calibration-selected Phase 2B fixed PyMatching model. The direct MLP was worse on the single test batch, while the PyMatching-residual MLP made no changes and tied matching. This small run is a pipeline check only. Historical NO-GO findings for adaptive switching and online weight updates remain in force. Do not present this dashboard as an adaptive-decoding result or a hardware demonstration.

## Layout

- `app.py`, `manager.py`, `storage.py`: local-only API, subprocess control, SQLite and WebSocket event delivery.
- `worker.py`: streaming Stim sampling, mini-batch training, validation, checkpoints, and test-only-after-training evaluation.
- `simulator.py`: thin adapter to the frozen categorical Phase 2B noise generator and calibration-selected PyMatching model.
- `models.py`, `qshift_stats.py`, `seed_protocol.py`, `telemetry.py`: small decoders, paired descriptive metrics, deterministic stream allocation and real hardware/system telemetry.
- `static/`: dependency-free HTML/CSS/JavaScript UI. Vanilla JS and Canvas were used instead of adding a Node build toolchain and chart dependencies; the page works offline once Python dependencies are installed.
