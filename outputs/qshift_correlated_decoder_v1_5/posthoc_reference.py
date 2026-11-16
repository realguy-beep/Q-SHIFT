"""POST-RUN, DESCRIPTIVE ONLY: privileged exact reference R_true on saved V1.5 arrays.

Frozen with the package, but not a decision endpoint. Decodes each saved
evaluation archive with the exact DEM logical-class decoder at the *true* q
(privileged; not deployable) and reports Bexact - R_true, i.e. how far the
deployable decoder sits from the DEM-exact ceiling. Read-only; writes only to
the given output directory. Usage: posthoc_reference.py <run_dir> <out_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from outputs.qshift_correlated_decoder_feasibility_v1_1.model import build_candidate_circuit  # noqa: E402
from outputs.qshift_v1_4b_decoder_optimality.mld import ExactLogicalDecoder  # noqa: E402

QS = (0.0, 0.01, 0.02)


def main() -> None:
    run, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    decs = {qi: ExactLogicalDecoder(build_candidate_circuit(q).detector_error_model(
        decompose_errors=False, approximate_disjoint_errors=True)) for qi, q in enumerate(QS)}
    errs = {"R_true": [0, 0, 0], "Bexact": [0, 0, 0], "disagree": [0, 0, 0]}
    shots = [0, 0, 0]
    for qi in range(3):
        for r in range(24):
            with np.load(run / "evaluation" / f"eval_q{qi}_r{r:02d}.npz", allow_pickle=False) as z:
                x, y, b = z["detectors"], z["observables"][:, 0], z["pred_Bexact"][:, 0]
            ref = decs[qi].decode(x, batch=256)[0][:, 0]
            errs["R_true"][qi] += int((ref != y).sum())
            errs["Bexact"][qi] += int((b != y).sum())
            errs["disagree"][qi] += int((ref != b).sum())
            shots[qi] += len(y)
    nz = lambda k: float(np.mean([errs[k][1] / shots[1], errs[k][2] / shots[2]]))  # noqa: E731
    result = {"label": "POST-RUN DESCRIPTIVE; privileged true-q exact reference; not a frozen endpoint",
              "errors_q0_q001_q002": errs, "shots": shots,
              "nonzero_ler": {"R_true": nz("R_true"), "Bexact": nz("Bexact")}}
    (out / "posthoc_reference.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
