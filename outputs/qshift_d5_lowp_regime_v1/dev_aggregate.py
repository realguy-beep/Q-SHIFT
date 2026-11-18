"""Apply the STAGE_S_PROTOCOL.md selection, headroom, stop and sizing rules. Writes DEV_SELECTION.json once.

Selection rules are the robustness Step D rules (qshift_d5_robustness_v1/dev_aggregate.py), unchanged.
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


def bits(path: Path, key: str, n: int) -> np.ndarray:
    with np.load(path) as z:
        return np.unpackbits(z[key])[:n].astype(bool)


def size_per_q(l2_nonzero_ler: float, phase1_n) -> int:
    """Shots per q so that L2 expects >= MIN_L2_NONZERO_ERRORS over both nonzero q, and >= the Phase 1 formula;
    rounded up to a multiple of ROOTS_PER_Q."""
    need = math.ceil(K.MIN_L2_NONZERO_ERRORS / (2 * l2_nonzero_ler))
    need = max(need, phase1_n or 0)
    return K.ROOTS_PER_Q * math.ceil(need / K.ROOTS_PER_Q)


def decision(r10) -> str:
    return "STOP" if (r10 is None or r10 < K.STOP_R) else "PROCEED_TO_STAGE_E_FREEZE"


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
        v, disc = {}, {}
        for qi in (1, 2):
            dlt = l2[sel][qi][0].astype(np.int64) - a_err[qi].astype(np.int64)
            v[qi] = float(dlt.var(ddof=1))
            disc[qi] = {"l2_only": int((l2[sel][qi][0] & ~a_err[qi]).sum()),
                        "astar_only": int((a_err[qi] & ~l2[sel][qi][0]).sum())}
        a_nz = int(a_err[1].sum()) + int(a_err[2].sum())
        L = a_nz / (2 * n)
        l2_nz = tab[f"{sel:.4f}"]["nonzero"]
        sizing_rate = max(l2_nz, 3) / (2 * n)        # zero L2 errors: rule-of-three upper rate (conservative)
        l2_q0 = tab[f"{sel:.4f}"]["errors_by_q"][0]
        phase1_n = math.ceil(1.96 ** 2 * (v[1] + v[2]) / 4 / (0.25 * L) ** 2) if L > 0 else None
        result[c] = {"family": K.CONDITIONS[c][0], "base_p": K.CONDITIONS[c][1], "shots_per_q": n,
                     "Astar_selected": astar, "Astar_errors_by_q": [int(a_err[qi].sum()) for qi in range(3)],
                     "matching_totals": total, "L2_grid": tab, "L2_selected_prior": sel, "L2_guard_failed": guard_failed,
                     "L2_eligible": eligible, "discordance_selected_vs_Astar": disc, "Astar_nonzero_ler": L,
                     "R_in_sample": 1 - l2_nz / a_nz if a_nz else None,
                     "floor_ratio_L2q0_over_Astar_nonzero": (l2_q0 / n) / L if L else None,
                     "cap_1_minus_floor_ratio": 1 - (l2_q0 / n) / L if L else None,
                     "phase1_N_required_per_q": phase1_n,
                     "stage_e_N_per_q": size_per_q(sizing_rate, phase1_n)}
    dec = decision(result["L10"]["R_in_sample"])
    js = {"schema": "qshift-d5-lowp-regime-dev-selection-v1", "conditions": result,
          "stop_rule": f"R_in_sample(L10) < {K.STOP_R}", "decision": dec,
          "label": ("REHEARSAL: not data" if rehearse else
                    "DEVELOPMENT ONLY: in-sample selection, headroom and sizing on Stage S shots; never reused for evaluation")}
    out.write_text(json.dumps(js, indent=2) + "\n", encoding="utf-8", newline="\n")
    for c, r in result.items():
        print(c, r["Astar_selected"], r["Astar_errors_by_q"], "| L2", {k: v["errors_by_q"] for k, v in r["L2_grid"].items()},
              "sel", r["L2_selected_prior"], "guard_failed", r["L2_guard_failed"], "| R", r["R_in_sample"],
              "cap", r["cap_1_minus_floor_ratio"], "| N_E", r["stage_e_N_per_q"])
    print("DECISION", dec)


if __name__ == "__main__":
    main()
