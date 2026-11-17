"""Apply the DEV_PROTOCOL.md selection and sizing rules. Writes DEV_SELECTION.json once.

Usage: dev_aggregate.py [--rehearse <out.json>]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import contract as K  # noqa: E402

N_EVAL_PER_Q = 200_016


def bits(path: Path, key: str, n: int) -> np.ndarray:
    with np.load(path) as z:
        return np.unpackbits(z[key])[:n].astype(bool)


def main() -> None:
    rehearse = "--rehearse" in sys.argv
    out = Path(sys.argv[sys.argv.index("--rehearse") + 1]) if rehearse else ROOT / "DEV_SELECTION.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists; aggregation runs once")
    tag = "dev_rehearsal" if rehearse else "dev"
    work, res = ROOT / "work" / tag, ROOT / ("work" if rehearse else "results") / f"{tag}_json"
    seeds = json.loads((ROOT / "DEV_SEEDS.json").read_text(encoding="utf-8"))["rehearsal_seeds" if rehearse else "seeds"]
    result = {}
    for c in K.CONDITIONS:
        recs = [json.loads((res / f"{c}_q{qi}_match.json").read_text(encoding="utf-8")) for qi in range(3)]
        for qi, r in enumerate(recs):
            if r["seed"] != seeds[K.dev_key(c, qi)]:
                raise RuntimeError(f"seed mismatch {c} q{qi}")
        n = recs[0]["shots"]
        names = list(recs[0]["matching_errors"])
        total = {nm: sum(r["matching_errors"][nm] for r in recs) for nm in names}
        # Phase 1 rule: min total over the three q; ties -> smaller q_dec, then ON before OFF.
        astar = min(names, key=lambda nm: (total[nm], float(nm.split("_")[2]), 0 if "_on_" in nm else 1))
        a_err = {qi: bits(work / f"{c}_q{qi}_match_errbits.npz", astar, n) for qi in range(3)}
        l2 = {}
        for pr in K.L2_PRIORS:
            e = {}
            for qi in range(3):
                r = json.loads((res / f"{c}_q{qi}_l2_{pr:.4f}.json").read_text(encoding="utf-8"))
                b = bits(work / f"{c}_q{qi}_l2_{pr:.4f}_errbits.npz", "err", n)
                if int(b.sum()) != r["errors"]:
                    raise RuntimeError("error-bit mismatch")
                e[qi] = (b, r["ms_per_shot"])
            l2[pr] = e
        tab = {f"{pr:.4f}": {"errors_by_q": [int(l2[pr][qi][0].sum()) for qi in range(3)],
                             "nonzero": int(l2[pr][1][0].sum() + l2[pr][2][0].sum()),
                             "ms_per_shot": float(np.mean([l2[pr][qi][1] for qi in range(3)]))} for pr in K.L2_PRIORS}
        a_q0 = int(a_err[0].sum())
        eligible = [pr for pr in K.L2_PRIORS if tab[f"{pr:.4f}"]["errors_by_q"][0] <= 1.10 * a_q0]
        if eligible:
            sel, guard_failed = min(eligible, key=lambda pr: (tab[f"{pr:.4f}"]["nonzero"], pr)), False
        else:
            sel, guard_failed = min(K.L2_PRIORS, key=lambda pr: (tab[f"{pr:.4f}"]["errors_by_q"][0], pr)), True
        # Sizing (Phase 1 formula) with the selected prior vs Astar_C.
        v, disc = {}, {}
        for qi in (1, 2):
            dlt = l2[sel][qi][0].astype(np.int64) - a_err[qi].astype(np.int64)
            v[qi] = float(dlt.var(ddof=1))
            disc[qi] = {"l2_only": int((l2[sel][qi][0] & ~a_err[qi]).sum()), "astar_only": int((a_err[qi] & ~l2[sel][qi][0]).sum())}
        L = (int(a_err[1].sum()) + int(a_err[2].sum())) / (2 * n)
        n_req = math.ceil(1.96 ** 2 * (v[1] + v[2]) / 4 / (0.25 * L) ** 2) if L > 0 else None
        result[c] = {"family": K.CONDITIONS[c][0], "base_p": K.CONDITIONS[c][1], "shots_per_q": n,
                     "Astar_selected": astar, "Astar_errors_by_q": [int(a_err[qi].sum()) for qi in range(3)],
                     "matching_totals": total, "L2_grid": tab, "L2_selected_prior": sel, "L2_guard_failed": guard_failed,
                     "L2_eligible": eligible, "discordance_selected_vs_Astar": disc, "Astar_nonzero_ler": L,
                     "N_required_per_q": n_req, "N_eval_per_q": N_EVAL_PER_Q,
                     "projected_under_powered": (n_req is None) or (n_req > N_EVAL_PER_Q)}
    js = {"schema": "qshift-d5-robustness-dev-selection-v1", "conditions": result,
          "label": ("REHEARSAL: not data" if rehearse else
                    "DEVELOPMENT ONLY: in-sample selection and sizing on Step D shots; never reused for evaluation")}
    out.write_text(json.dumps(js, indent=2) + "\n", encoding="utf-8", newline="\n")
    for c, r in result.items():
        print(c, r["Astar_selected"], r["Astar_errors_by_q"], "| L2", {k: v["errors_by_q"] for k, v in r["L2_grid"].items()},
              "sel", r["L2_selected_prior"], "guard_failed", r["L2_guard_failed"], "| N_req", r["N_required_per_q"],
              "under", r["projected_under_powered"])


if __name__ == "__main__":
    main()
