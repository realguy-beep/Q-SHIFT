# Q-SHIFT Science Exhibition Demo

A local, single-laptop demonstration of quantum error correction using **real Stim circuit sampling** and **real PyMatching decoding**. The dark cyan/violet page is designed for a school science exhibition and does not need a cloud service or login.

## Start on Windows

1. Install Python 3.10 or newer and enable **Add Python to PATH**.
2. Double-click `START_WINDOWS.bat`.
3. On the first launch, the script creates an isolated `.venv` and installs the pinned packages in `requirements.txt`. This first installation needs internet access.
4. The script starts the local server and opens `http://127.0.0.1:8765` after its health endpoint responds. Keep the command window open while using the site; press **Ctrl+C** there to stop it.
5. Later launches use the already-installed virtual environment and work offline. No CDN, remote font, cloud database, or remote simulation service is used. The optional GitHub links need internet.

Manual commands from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe server.py
```

To run the automated checks, install test-only packages once and run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe -m pytest -q
```

## What a live run does

- Supports 1,000, 5,000, or 10,000 **evaluation** shots and five listed burst probabilities (0, 0.4%, 0.8%, 1.2%, 1.6%).
- Builds a distance-3, five-round rotated Z-memory Stim circuit with 40 detectors and one logical observable.
- Uses 2,000 separate detector-only calibration shots. It also generates 17 independent detector-profile reference batches of 1,200 shots each (20,400 reference shots). The page reports these streams separately from evaluation.
- Estimates burst probability from calibration detector frequencies only. It does not pass logical-observable labels or the generating probability into the estimator.
- Builds a burst-blind fixed PyMatching decoder and a decoder using the estimated burst probability. Both decode the **same evaluation detector rows**; errors are scored against those rows’ simulated observable labels.
- Updates progress only after sampling and decoding each batch. `generated_shots` and `completed_shots` are separate backend fields. The two error counts, paired decoder disagreements, selected estimate, and measured elapsed time come from the run.
- Stores the active run ID in the browser tab’s session storage so refresh or a short connection interruption can reconnect while the same server process remains alive. The server keeps run status in memory; restarting the server loses that status and the page will say so rather than reconstructing results.

## Scientific scope and limits

This is an **educational live simulation**, not the frozen Stage 5 research runner and not a hardware demonstration. It adds the synthetic paired-X event after each of five `MR` instructions in Stim’s generated circuit and uses `decompose_errors=True, approximate_disjoint_errors=True` when constructing the matching graph. The demo’s 17-point detector-profile estimator is a simplified nearest-profile procedure; it is not the exact frozen Stage 5 implementation. Do not pool or present live demo results as additional Stage 5 shots.

The lattice in the hero is decorative. The interactive 40-cell view is an **ordinal detector-index map**, not a surface-code layout or detector-coordinate map. Its highlights show detector indices triggered in the most recently completed evaluation batch. Before a real run, its animation is labeled illustrative and is not progress data.

The published **21.9% relative reduction** is a separate Stage 5 aggregate comparing detector-profile adaptation with a nominal burst-blind fixed decoder under the frozen synthetic conditions. It is not a live-run result, a claim over every strong static decoder, or a hardware result. The live demo uses a simpler circuit insertion and estimator and may produce different outcomes.

## Implementation and compatibility

The tested Windows environment uses Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3, FastAPI 0.162.0, and Uvicorn 0.54.0. PyMatching graphs are constructed with correlation decoding disabled, and the code calls `decode_batch(detectors)` without `enable_correlations=True`. This directly avoids the prior configuration error instead of suppressing it.

The server binds to `127.0.0.1` only. A single-worker pool and a lock reject overlapping runs. Backend exceptions are returned as a useful run error and the full traceback is written to the local server console. No experimental output is written into the Q-SHIFT research evidence directories.

## Files

- `server.py` — local FastAPI backend and Stim/PyMatching experiment.
- `index.html` — responsive exhibition interface.
- `tests/` — regression and real-run API tests.
- `requirements.txt` — pinned runtime packages.
- `requirements-test.txt` — test-only packages.
- `START_WINDOWS.bat` — isolated one-click launcher.
