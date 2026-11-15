"""EXPLORATORY DIAGNOSTIC (planning input for V1.3; not evidence for any claim).

Sweeps the five-factor burst prior per condition on the already-exposed V1.1
selection set (30 x 2,000 shots), with residual matching correlations ON (as
frozen) and OFF, to test whether the static-weight cost / correlated-decode
mismatch (H1) explains why a smaller-than-true prior wins. No sampling; V1.2
evaluation data are not read.
"""
import json, math, sys
from pathlib import Path
import numpy as np
REPO = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(REPO))
from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (
    build_base_circuit, build_decomposed_dem, build_matching, extract_burst_events)
from outputs.qshift_correlated_decoder_v1_2.multi_prior import MultiPriorFiveFactor
from outputs.qshift_correlated_decoder_v1_2.select_static import load_selection_set

GRID = [0.0005, 0.001, 0.0025, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02]
run = Path(sys.argv[1]).resolve()
_, data = load_selection_set(run)
base = build_matching(build_decomposed_dem(build_base_circuit()))
events = extract_burst_events()
out = {"label": __doc__.strip().splitlines()[0], "grid": GRID, "variants": {}}
for corr in (True, False):
    dec = MultiPriorFiveFactor(base, events)
    orig = dec.matching.decode_to_edges_array
    dec.matching = type("M", (), {"decode_to_edges_array": staticmethod(
        lambda s, enable_correlations=True, _o=orig, _c=corr: _o(s, enable_correlations=_c))})()
    errs = {str(c): {str(q): 0 for q in GRID} for c in (0.0, 0.01, 0.02)}
    for (qi, _), (x, y, _) in sorted(data.items()):
        c = str((0.0, 0.01, 0.02)[qi])
        for row, yy in zip(x, y):
            opts = dec._options(row)
            for q in GRID:
                errs[c][str(q)] += int(dec._choose(opts, q) != yy)
    out["variants"]["correlations_on" if corr else "correlations_off"] = errs
    print("corr" if corr else "nocorr", {c: min(v, key=v.get) for c, v in errs.items()},
          {c: v for c, v in errs.items()})
(Path(__file__).parent / "diag_prior_calibration.json").write_text(json.dumps(out, indent=2) + "\n")
