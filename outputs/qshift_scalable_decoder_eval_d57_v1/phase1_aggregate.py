"""Phase 1 aggregation: selection, sizing and Phase 2 projection (PHASE1_PROTOCOL.md + Addendum A).

Reads results/phase1_json/*.json and work/phase1/*_errbits.npz. Writes PHASE1_RESULTS.json once.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "PHASE1_RESULTS.json"
QS = (0.0, 0.01, 0.02)
SHOT_CAP, WALL_CAP_S, WORKERS, CONTENTION, OVERHEAD_S = 6_000_000, 36_000, 8, 1.25, 600
CAL_SHOTS_PER_D = 72 * 500


def load(d):
    js = {q: json.loads((ROOT / "results" / "phase1_json" / f"d{d}_q{q:.2f}.json").read_text(encoding="utf-8")) for q in QS}
    bits = {}
    for q in QS:
        with np.load(ROOT / "work" / "phase1" / f"d{d}_q{q:.2f}_errbits.npz") as z:
            n = int(z["n"])
            bits[q] = {k: np.unpackbits(z[k])[:n].astype(bool) for k in z.files if k != "n"}
    return js, bits


def main() -> None:
    if OUT.exists():
        raise SystemExit("PHASE1_RESULTS.json exists; aggregation runs once")
    per_d = {}
    for d in (5, 7):
        js, bits = load(d)
        names = list(js[0.0]["matching"])
        totals = {nm: sum(js[q]["matching"][nm] for q in QS) for nm in names}

        def key(nm):
            _, mode, qd = nm.split("_")
            return (totals[nm], float(qd), 0 if mode == "on" else 1)
        astar = min(names, key=key)
        ff_tot = {p: sum(js[q]["five_factor"][p] for q in QS) for p in js[0.0]["five_factor"]}
        boff = min(ff_tot, key=lambda p: (ff_tot[p], float(p)))
        n = {q: js[q]["shots"] for q in QS}
        ler = {arm: {str(q): (bits[q][arm].sum() / n[q]) for q in QS} for arm in (astar, "match_off_0.0", "V3_2")}
        disc, v = {}, {}
        for q in (0.01, 0.02):
            a, b = bits[q][astar], bits[q]["V3_2"]
            n10, n01 = int((b & ~a).sum()), int((a & ~b).sum())
            delta = (n10 - n01) / n[q]
            v[q] = (n10 + n01) / n[q] - delta ** 2
            disc[str(q)] = {"V3_2_only_errors": n10, "Astar_only_errors": n01, "delta": delta, "var_per_shot": v[q]}
        L = float(np.mean([ler[astar]["0.01"], ler[astar]["0.02"]]))
        target = 1.96 ** 2 * (v[0.01] + v[0.02]) / 4 / (0.25 * L) ** 2
        N = int(math.ceil(target / 24) * 24)
        t = {q: js[q]["timing_ms_per_shot"] for q in QS}
        mean_ms = lambda k: float(np.mean([t[q][k] for q in QS])) if k in t[0.0] else None  # noqa: E731
        cost_core = 2 * mean_ms("matching_one_arm") + mean_ms("five_factor_grid16") + mean_ms("V3_2")
        per_d[d] = {"Astar_selected": astar, "Astar_total_errors": totals[astar], "BoffStatic_prior": float(boff),
                    "BoffStatic_total_errors_subsample": ff_tot[boff], "five_factor_shots_per_q": js[0.0]["five_factor_shots"],
                    "ler": ler, "V3_2_errors_by_q": {str(q): js[q]["V3_2_errors"] for q in QS},
                    "discordance": disc, "Astar_nonzero_ler": L, "N_per_q_target": N,
                    "cost_ms_per_shot": {"core_arms": cost_core, "V3_numpy": mean_ms("V3_numpy")},
                    "matching_totals": totals, "five_factor_totals": ff_tot,
                    "timing_ms_per_shot_by_q": {str(q): t[q] for q in QS}}

    def project(include_v3: bool, scale: float):
        shots = cpu = 0.0
        for d in (5, 7):
            nq = int(math.floor(per_d[d]["N_per_q_target"] * scale / 24) * 24)
            c = per_d[d]["cost_ms_per_shot"]["core_arms"] + ((per_d[d]["cost_ms_per_shot"]["V3_numpy"] or 0) if (include_v3 and d == 5) else 0)
            shots += 3 * nq + CAL_SHOTS_PER_D
            cpu += 3 * nq * c / 1000
        return shots, cpu / WORKERS * CONTENTION + OVERHEAD_S

    def fit(include_v3):
        s_shots, s_wall = project(include_v3, 1.0)
        scale = min(1.0, (SHOT_CAP - 2 * CAL_SHOTS_PER_D) / (s_shots - 2 * CAL_SHOTS_PER_D),
                    (WALL_CAP_S - OVERHEAD_S) / (s_wall - OVERHEAD_S))
        return scale, project(include_v3, scale)

    scale_core, (shots_core, wall_core) = fit(False)
    scale_v3, (shots_v3, wall_v3) = fit(True)
    include_v3 = scale_v3 >= scale_core and scale_v3 >= 1.0 - 1e-12
    scale, shots, wall = (scale_v3, shots_v3, wall_v3) if include_v3 else (scale_core, shots_core, wall_core)
    plan = {}
    for d in (5, 7):
        nq = int(math.floor(per_d[d]["N_per_q_target"] * scale / 24) * 24)
        plan[str(d)] = {"N_per_q": nq, "shots_per_root": nq // 24, "target_N_per_q": per_d[d]["N_per_q_target"],
                        "projected_underpowered": nq < per_d[d]["N_per_q_target"]}
    out = {"schema": "qshift-d57-phase1-results-v1", "per_distance": {str(d): v for d, v in per_d.items()},
           "phase2_plan": {"scale": scale, "include_V3_numpy_d5": include_v3, "per_distance": plan,
                           "projected_total_shots": shots, "projected_wall_seconds": wall,
                           "caps": {"shots": SHOT_CAP, "wall_seconds": WALL_CAP_S, "workers": WORKERS,
                                    "contention": CONTENTION, "overhead_seconds": OVERHEAD_S}},
           "label": "DEVELOPMENT ONLY: Phase 1 selection/sizing; in-sample selection; V3.2 at true q (sizing input only)"}
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out["phase2_plan"], indent=1))
    for d in (5, 7):
        p = per_d[d]
        print(d, p["Astar_selected"], "BoffStatic", p["BoffStatic_prior"], "L", round(p["Astar_nonzero_ler"], 6),
              "ler", {a: {q: round(x, 6) for q, x in v.items()} for a, v in p["ler"].items()}, "disc", p["discordance"])


if __name__ == "__main__":
    main()
