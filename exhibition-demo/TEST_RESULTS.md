# Q-SHIFT exhibition demo — verification record

Date: 9 November 2026 (Asia/Calcutta)
Source: supplied `QSHIFT_Exhibition_Website_FIXED.zip`, modified only under `exhibition-demo/`.

## Environment

- Windows, Python 3.12.10 in `exhibition-demo/.venv`.
- Stim 1.16.0; PyMatching 2.4.0; NumPy 2.5.3; FastAPI 0.162.0; Uvicorn 0.54.0.
- Test-only packages: pytest 9.1.1 and httpx 0.28.1.
- The pinned runtime requirements installed successfully into the isolated virtual environment; `pip check` reported no broken requirements.

## Automated tests

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests
```

Result: **13 passed**. The suite includes actual Stim/PyMatching API runs at 1,000, 5,000, and 10,000 evaluation shots at burst probability 0.008; a 1,000-shot zero-burst run; exact evaluation count and rate recomputation; detector/observable shape checks; paired-input checks; the PyMatching correlation-mode regression; unsupported input rejection; concurrent request rejection; injected decoder failure followed by a successful retry; generated-versus-completed accounting after an injected batch failure; and frontend checks for distinct counters and session-based reconnection.

The test run emitted one Starlette deprecation warning concerning its current `TestClient`/httpx integration. It did not fail the tests. The test API behavior worked in the pinned environment.

Frontend JavaScript syntax check:

```powershell
node -e "const fs=require('fs'); const h=fs.readFileSync('index.html','utf8'); const a=h.indexOf('<script>')+8,b=h.lastIndexOf('</script>'); new Function(h.slice(a,b)); console.log('PASS')"
```

Result: **PASS**.

## Visible browser runs

The local Uvicorn server was opened at `http://127.0.0.1:8765`. Browser runs were driven from the page controls; returned status, progress, decoder counts, estimates, and elapsed times were read from the visible UI.

| Run | Completed evaluation shots | Fixed errors / LER | Adaptive errors / LER | Detector-profile estimate | Observed elapsed |
|---|---:|---:|---:|---:|---:|
| Burst 0.008, quick | 1,000 | 5 / 0.500% | 5 / 0.500% | 0.000 | 0.25 s |
| Burst 0.008, full | 10,000 | 83 / 0.830% | 66 / 0.660% | 0.008 | 0.31 s |
| Burst 0.000, quick | 1,000 | 5 / 0.500% | 5 / 0.500% | 0.006 | 0.27 s |
| Retry after server restart, burst 0.008 | 1,000 | 6 / 0.600% | 5 / 0.500% | 0.006 | 0.27 s |

The 5,000-shot 0.008 case also completed through the automated API test with exactly 5,000 generated and decoded evaluation rows. Each completed run reported 2,000 calibration shots and 20,400 independent profile-reference shots separately from evaluation.

These are small, individual stochastic demonstrations, not a performance study. In particular, the 2,000-shot estimator selected 0.000 for one 0.008 run and 0.006 for one zero-burst run. This is direct evidence that the educational profile estimate can be noisy; the UI reports the estimate and warns that this demo is not a Stage 5 replication. The single 10,000-shot improvement is not evidence of general superiority.

## Failure and retry checks

- Injected a decoder-construction exception through the API: the job entered `error`, returned the actual exception summary, and logged the traceback locally. A new run then completed successfully.
- Injected a decoder failure after Stim produced a 500-row batch: `generated_shots=500` and `completed_shots=0`; the failed batch was not represented as decoded progress.
- Sent a second request while a first request was held active: API returned HTTP 429, preserving the one-run-at-a-time rule.
- Stopped the local server during browser use: the page displayed a local-server recovery instruction and re-enabled retry. After restarting the same server entry point, a fresh browser run completed and the button returned to its normal state.
- Verified that progress refreshes from the same server’s in-memory run state when the page retains its run ID in `sessionStorage`. A full server restart cannot restore in-memory results; the UI reports that status as unavailable rather than inventing progress.

## One-click startup and scope

`START_WINDOWS.bat` was executed from the demo directory. With dependencies already installed, it skipped pip and started the server on loopback; `/api/health` returned Stim 1.16.0 and PyMatching 2.4.0, and `/` returned HTTP 200. The server was stopped after verification. It is not left running.

The app has no external script, font, or stylesheet dependencies. Optional GitHub links require internet; core simulation is local after setup. All code, tests, logs, and generated files are under `exhibition-demo/` or the final demo ZIP. No frozen research source, Stage 5 output, published statistic, or experiment directory was changed, and no Stage 5 samples were generated.
