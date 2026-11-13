# Main Codex handoff: experimental BeliefMatching adapter

## Status

BeliefMatching is **working and computationally feasible for bounded Q-SHIFT d3 deterministic development comparisons**, subject to the DEM alias guard below. This is not evidence of lower logical error rate. The candidate is experimental and disabled by default; do not register it without explicit NS-2C experimental opt-in.

## Source files

- `beliefmatching_adapter.py` — isolated adapter, explicit model identity metadata, DEM compatibility checks, optional NS-2C binding.
- `test_beliefmatching_adapter.py` — 14 deterministic tests.
- `benchmark_beliefmatching.py` and `benchmark_results_ns3b.json` — bounded deterministic runtime measurements.
- `requirements-ns3b.lock.txt` — exact dependency freeze.
- `BELIEFMATCHING_SOURCE_AUDIT.md`, `ALIAS_COLLISION_FINDING.md`, `RESOURCE_AND_CORRECTNESS_RESULTS.md` — implementation, limitation, and evidence reports.

The main checkout's NS-2C source was read-only inspected at `qshift_core_v1/contracts.py`, `sampling_model_identity.py`, and `decoder_runtime_v2.py`. Its SHA-256 hashes are recorded in `SOURCE_MANIFEST.json`. The adapter returns `DecoderPrediction` from `decode(detectors)`, uses `DecoderMetadata` with `experimental=True`, constructs a distinct `DecoderModelIdentity`, and was exercised through `CheckedDecoderAdapter` and `CompatibilityAwareDecoderBank`. Registration was rejected without `experimental_opt_in=True` and succeeded with it. Runtime construction also verifies the installed package version and pinned source-module digest. No main or research worktree was modified.

## Reproduce

From the standalone NS-3 workspace (PowerShell):

```powershell
py -3.12 -m venv .venv_beliefmatching_ns3b
git clone https://github.com/oscarhiggott/BeliefMatching.git upstream/BeliefMatching
git -C upstream/BeliefMatching checkout 4458c278bbec273c8c1a26411dadccc49222f8ef
.\.venv_beliefmatching_ns3b\Scripts\python.exe -m pip install -e .\upstream\BeliefMatching
.\.venv_beliefmatching_ns3b\Scripts\python.exe -m pip install -r outputs\qshift_ns3_decoder_research\ns3b_beliefmatching\requirements-ns3b.lock.txt
Set-Location outputs\qshift_ns3_decoder_research\ns3b_beliefmatching
..\..\..\.venv_beliefmatching_ns3b\Scripts\python.exe -m unittest -v test_beliefmatching_adapter
..\..\..\.venv_beliefmatching_ns3b\Scripts\python.exe benchmark_beliefmatching.py
```

The command set uses the pinned commit and local venv only. In other environments, install from the exact commit and apply `requirements-ns3b.lock.txt`; do not install into a shared/global interpreter.

If the NS-2B/NS-2C source package is not the sibling workspace used here, set `QSHIFT_NS2B_ROOT` to the directory containing `qshift_core_v1` before running the integration test. That source is an external read-only dependency; its three consumed files and hashes are listed in `SOURCE_MANIFEST.json`.

## Construction and identity requirements

Build the candidate from `circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)` under the current Q-SHIFT model settings. Provide explicit generating-noise identity and separate assumed decoder-noise provenance. Build the NS-2C `SamplingIdentity` from the sampling circuit, a `StimDEMArtifact`/`DEMConstructionRecord` for the concrete DEM, then call `adapter.bind_ns2c(...)`. Its model identity records upstream version/commit, DEM digest, assumed-noise identity, exact detector order, observable semantics, and sampling identity separately. Inputs remain unpacked binary uint8 in `[shots, detectors]`; outputs are binary uint8 `[shots, observables]` in Stim order.

Do not use this adapter with a DEM that has the same detector support assigned different logical-observable parity, repeated targets inside a decomposed component, or a component with more than two detectors. The pinned upstream maps supports to a single observable support and otherwise can silently lose distinctions; the adapter rejects these cases. The tested Q-SHIFT DEM passes.

## Performance and caveats

On five fixed Q-SHIFT rows, warm BM batch inference was 0.415 ms and PyMatching ordinary/correlation-enabled batches were 0.005/0.008 ms; graph construction was 19/1.30/1.50 ms, respectively. No labeled outcomes were scored. The selected fixture set is tiny and deterministic; no LER conclusions or general runtime guarantee follow. Native memory was not measured. If fallback frequency or larger circuits drive cost, evaluate an optimized belief-matching/BP-assisted matching implementation next, not a rewritten algorithm.

## Scientific follow-on gate

Before any stochastic development study, freeze the strong static PyMatching baseline, the same decomposed DEM/model information for all arms, any true-parameter arm separately as privileged, independent root splits, paired scoring/cluster inference, practical margin, runtime limits, and the exact alias checks. No such experiment is authorized by this handoff. Historical V2.4 remains HOLD.
