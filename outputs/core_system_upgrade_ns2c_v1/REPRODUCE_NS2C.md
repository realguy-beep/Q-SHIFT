# Reproduce NS-2C deterministic validation

Run from the repository root in the installed project environment. These commands build a deterministic Stim circuit/DEM fixture and decode manually supplied detector arrays. They do not call a Stim sampler or access research evaluation data.

```powershell
python -m unittest dashboard.tests.test_decoder_runtime_v2 -v
python -m unittest dashboard.tests.test_decoder_runtime_v2 dashboard.tests.test_sampling_model_identity_v2 dashboard.tests.test_circuit_identity_v1 dashboard.tests.test_core_system_v1 -v
python -m compileall -q qshift_core_v1\decoder_runtime_v2.py dashboard\tests\test_decoder_runtime_v2.py
```

Expected selected regression-suite result: **70 tests passed**.

## Research decoder integration sketch

```python
from qshift_core_v1.decoder_runtime_v2 import (
    CheckedDecoderAdapter, CompatibilityAwareDecoderBank, evaluate_paired_batch,
)

# `sampling`, `decoder_model`, and `batch` are the explicit NS-2B identities.
# `research_decoder` implements decode(detectors) -> DecoderPrediction.
adapter = CheckedDecoderAdapter(
    research_decoder,
    model_identity=decoder_model,
    sampling_identity=sampling,
)
bank = CompatibilityAwareDecoderBank(sampling)
bank.register(adapter, experimental_opt_in=True)  # only for an explicit development integration
# Register the unchanged fixed PyMatching adapter separately and use it as baseline.
report = evaluate_paired_batch(
    bank,
    batch,
    decoder_names=("pymatching_fixed", "research_decoder"),
    baseline_name="pymatching_fixed",
    scope="development",
    sample_id="declared-development-block-id",
    observables=development_labels,
)
```

The wrapper provides each implementation only a defensive detector matrix. Labels are consumed after every requested decoder returns. Do not pass protected-test labels; `protected-test` scope is rejected. A decoder's assumed DEM/noise provenance must describe its own model and can differ from the generating circuit while retaining the same sampling identity.
