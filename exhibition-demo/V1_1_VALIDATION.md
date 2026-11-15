# Q-SHIFT Exhibition Demo V1.1 Validation

## Scope

Validated the laptop application from the isolated branch `codex/qshift-exhibition-demo-v1.1`, based on V1 commit `e1edda10dd7aa2cfe54b2a870edbaf621e38ac4c`. The only product-code change in this validation is a local Stage 5 result-row layout correction plus an embedded data-URI favicon. Screenshots are actual captures of the running local application.

The two Mode C runs below are bounded **software smoke tests only**. Their generated observations are not Stage 5 evidence, are not written to research output directories, and must not be pooled with research results.

## Windows startup

From the repository's `exhibition-demo` folder, double-click `START_WINDOWS.bat`. On first launch it creates `.venv` and installs the pinned `requirements.txt` dependencies (Internet is needed for that setup). Keep the console window open; the launcher opens `http://127.0.0.1:8765` when `/api/health` is ready. To stop the server, focus its console and press Ctrl+C. Once dependencies are installed, the application uses local Python packages and localhost only. The GitHub link is user activated.

Validation used Python 3.12.10, Stim 1.16.0, and PyMatching 2.4.0. The launcher started the local Uvicorn server successfully; the page, health endpoint, and deterministic fixture endpoint responded. The HTML uses system fonts, inline CSS/JavaScript, and an embedded favicon, with no remote runtime assets.

## Mode checks

- **Mode A:** advanced and reset the deterministic teaching sequence. The fixed DEM fixture endpoint returned the same deterministic fixture twice; it is labeled as an approximate DEM mechanism, not a sampled circuit history. Reset returned the walkthrough to the clean first step.
- **Mode B:** displayed frozen Stage 5 aggregates accurately: nominal fixed 0.707165%, adaptive 0.552570%, privileged true-p 0.552463%, and 21.86% relative reduction versus nominal fixed. The text states that this is not evidence of superiority over a well-tuned burst-aware static decoder and is not a hardware result. A layout fix now separates labels from values.
- **Mode C:** two repeatability smoke runs completed at generating burst probability `p=0.008`, each with exactly 1,000 evaluation shots. Each reported 2,000 detector-only calibration shots and 20,400 separate profile-reference shots outside the evaluation count. The fixed, adaptive, and oracle-only privileged decoders all returned results for the same evaluation detector rows. The server computes paired predictions and scores them against the same observable labels.

| Run | Fixed errors / LER | Adaptive errors / LER | Privileged errors / LER | Detector-only estimate | Backend elapsed | Click to completed display observed |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 4 / 0.400% | 3 / 0.300% | 3 / 0.300% | 0.003 | 0.28 s | 7.20 s |
| 2 | 5 / 0.500% | 4 / 0.400% | 4 / 0.400% | 0.009 | 0.36 s | 9.25 s |

Displayed LERs equal the corresponding error count divided by 1,000. The click-to-display measurement includes browser/UI observation overhead; backend elapsed is the server's monotonic run timer. The estimated values differ from the selected generating probability, as expected for this simplified finite-sample detector-only demonstration. These outcomes establish software completion only; they are not decoder-performance evidence.

The interface permitted a second run after the first completed and replaced the current result without corrupting the page. Unsupported API inputs were rejected with HTTP 422 in deterministic tests. Backend exception UX was not fault-injected during this validation because that existing fault test starts a real sampled run.

## Screenshots

Captured from the running Windows application (JPEG bytes, named `.jpg`):

- [Mode A — deterministic walkthrough and fixture](screenshots/mode-a.jpg) — 1536 × 864.
- [Mode B — frozen Stage 5 result](screenshots/mode-b.jpg) — 1536 × 864.
- [Mode C — completed live run and results](screenshots/mode-c-results.jpg) — 1536 × 864.
- [Mode C — run controls](screenshots/mode-c.jpg) — 1536 × 864.
- [Mode B — reduced-width layout](screenshots/mode-b-narrow.jpg) — 775 × 854.
- [Mode C — reduced-width result cards](screenshots/mode-c-narrow.jpg) — 775 × 854.

At reduced width, Stage 5 labels and values remain separated and the three live result cards reflow without overlapping. In the two-column result layout, the privileged card continues on the next row and is reachable by scrolling.

## Offline and hardware status

The page and simulation run locally, binds to `127.0.0.1`, and makes no automatic remote asset requests; no CDN, remote font, cloud service, or remote simulation endpoint is used. Offline behavior was confirmed by source/configuration inspection and successful localhost execution, but the laptop's network connection was not disabled systemwide during the run. This check does not establish first-time package installation offline.

Hardware remains unconnected. The nine-LED preview and draft serial protocol remain software-only; no ESP32 pinout, physical LED index, or power wiring was selected.

## Deterministic tests

Command, from `exhibition-demo`:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_deterministic_exhibition.py tests/test_demo.py::test_api_rejects_unsupported_inputs tests/test_demo.py::test_health_and_served_page tests/test_demo.py::test_both_decoder_arms_receive_identical_detector_rows tests/test_demo.py::test_frontend_progress_and_offline_assets_are_explicit
```

Result: **8 passed** in 3.88 seconds; one Starlette deprecation warning notes that `httpx` with `starlette.testclient` is deprecated. The selected tests made no Stim shot-sampling calls. The complete legacy suite was not run because it includes additional live sampling tests outside this bounded smoke-test allocation.

## Remaining limits

- Mode C uses a simplified circuit/profile estimator and is explicitly not a Stage 5 replication.
- The privileged true-p arm uses the selected generating parameter and is oracle-only.
- The live smoke counts are too small and were not designed for inference; no superiority claim follows.
- Internet was not disabled at the operating-system level; offline readiness is supported by local-only runtime dependencies and source inspection, with the limitation stated above.
- No physical components were available for wiring or serial validation.
