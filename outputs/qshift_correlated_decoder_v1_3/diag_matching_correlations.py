"""EXPLORATORY DIAGNOSTIC (planning input for V1.3; not evidence for any claim).

Plain PyMatching on the V1.1 selection set over the static-q grid, with
enable_correlations True (as in V1.1/V1.2) and False. No sampling.
"""
import json, sys
from pathlib import Path
import numpy as np
REPO = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(REPO))
from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (
    build_candidate_circuit, build_decomposed_dem, build_matching)
from outputs.qshift_correlated_decoder_v1_2.select_static import load_selection_set
GRID = [0.0, 0.0025, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02]
_, data = load_selection_set(Path(sys.argv[1]).resolve())
out = {"label": __doc__.strip().splitlines()[0], "grid": GRID}
for corr in (True, False):
    t = {}
    for q in GRID:
        m = build_matching(build_decomposed_dem(build_candidate_circuit(q)))
        e = [0, 0, 0]
        for (qi, _), (x, y, _) in data.items():
            p = np.asarray(m.decode_batch(x, enable_correlations=corr)).reshape(-1)
            e[qi] += int(np.count_nonzero(p != y))
        t[str(q)] = e
    out["correlations_on" if corr else "correlations_off"] = t
    print("ON " if corr else "OFF", {q: (v, sum(v)) for q, v in t.items()})
(Path(__file__).parent / "diag_matching_correlations.json").write_text(json.dumps(out, indent=2) + "\n")
