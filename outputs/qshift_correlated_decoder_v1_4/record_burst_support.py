"""Record the burst-support rule's output for every gate distance (sampler-free).

Committed before any d>=5 sampling so the support cannot be chosen after seeing
decoder performance. Writes BURST_SUPPORT.json; refuses to overwrite.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m

out = ROOT / "BURST_SUPPORT.json"
if out.exists():
    raise SystemExit("BURST_SUPPORT.json exists; it is recorded once")
record = {"schema": "qshift-v1.4-burst-support-v1", "rule": m.__doc__.split("Burst support")[1].strip(),
          "sampler_calls": 0, "entries": []}
for d in (3, 5, 7):
    spec = m.CodeSpec(distance=d)
    grid = {q: c for c, q in m.data_qubit_grid(spec).items()}
    for family in m.BURST_FAMILIES:
        qubits = m.burst_qubits(spec, family)
        events = m.extract_burst_events(spec, qubits)
        record["entries"].append({
            "distance": d, "family": family, "qubits": list(qubits),
            "grid_cells_col_row": [list(grid[q]) for q in qubits],
            "detectors_per_event": [len(e.detector_ids) for e in events],
            "observable_flip_per_event": [e.observable_flip for e in events],
            "events": [list(e.detector_ids) for e in events]})
        print(d, family, qubits, [len(e.detector_ids) for e in events], [e.observable_flip for e in events])
out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
