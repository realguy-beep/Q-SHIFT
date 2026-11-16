"""Pre-registered V3 d=3 quality statistics (PROTOCOL.md). Reads work/d3/root_*.npz.

Equal-weight nonzero LER over q in {0.01, 0.02}; root-paired bootstrap (20,000 replicates,
seed 20261116); gap recovery G = (LER_Astar - LER_V3) / (LER_Astar - LER_Bexact);
agreement with the exact reference Bexact. Writes QUALITY_D3.json once.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "QUALITY_D3.json"
ARMS = ("Astar", "BoffStatic", "Bexact", "V3_min", "V3_lc")
BOOT, SEED, N = 20000, 20261116, 24


def main() -> None:
    if OUT.exists():
        raise SystemExit("QUALITY_D3.json exists; runs once")
    data = {}
    for qi in range(3):
        for r in range(N):
            with np.load(ROOT / "work" / "d3" / f"root_q{qi}_r{r:02d}.npz") as z:
                data[(qi, r)] = {k: z[k] for k in z.files}
    err = {(a, qi, r): (data[(qi, r)][a] != data[(qi, r)]["y"]) for a in ARMS for qi in range(3) for r in range(N)}
    rate = {k: float(v.mean()) for k, v in err.items()}
    totals = {a: [int(sum(err[(a, qi, r)].sum() for r in range(N))) for qi in range(3)] for a in ARMS}
    shots = [sum(len(data[(qi, r)]["y"]) for r in range(N)) for qi in range(3)]
    nz = {a: float(np.mean([totals[a][1] / shots[1], totals[a][2] / shots[2]])) for a in ARMS}
    q0 = {a: totals[a][0] / shots[0] for a in ARMS}
    rng = np.random.default_rng(SEED)
    idx = {qi: rng.integers(0, N, size=(BOOT, N)) for qi in range(3)}

    def paired(x, b):
        d = {qi: np.asarray([rate[(x, qi, r)] - rate[(b, qi, r)] for r in range(N)]) for qi in range(3)}
        boot = np.mean([d[qi][idx[qi]].mean(axis=1) for qi in (1, 2)], axis=0)
        return {"nonzero_estimate": float(np.mean([d[1].mean(), d[2].mean()])),
                "nonzero_95ci": np.quantile(boot, [0.025, 0.975]).tolist(), "q0_estimate": float(d[0].mean())}

    contrasts = {f"{x}_minus_{b}": paired(x, b) for x in ("V3_min", "V3_lc") for b in ("Astar", "BoffStatic", "Bexact")}
    gap = {x: (nz["Astar"] - nz[x]) / (nz["Astar"] - nz["Bexact"]) for x in ("V3_min", "V3_lc", "BoffStatic")}
    agree = {x: float(np.mean(np.concatenate([data[k][x] == data[k]["Bexact"] for k in data]))) for x in ("V3_min", "V3_lc", "Astar")}
    ms = {v: 1000 * float(np.mean([data[k][f"sec_{v}"] for k in data])) for v in ("min", "lc")}
    osd = float(np.mean([data[k]["used_osd"] for k in data])) / len(next(iter(data.values()))["y"])

    def decision(x):
        c = contrasts[f"{x}_minus_Astar"]
        beats = c["nonzero_95ci"][1] < 0
        quality = beats and gap[x] >= 0.50 and (q0[x] - q0["Astar"]) <= 0.0005
        return {"beats_Astar_ci": beats, "gap_recovery_ge_0_50": gap[x] >= 0.50,
                "q0_not_worse_by_0_05pp": (q0[x] - q0["Astar"]) <= 0.0005, "d3_quality_criteria_met": quality}

    out = {"schema": "qshift-scalable-v3-quality-d3-v1", "rows_per_root": int(len(next(iter(data.values()))["y"])),
           "errors_q0_q001_q002": totals, "nonzero_ler": nz, "q0_ler": q0, "contrasts": contrasts,
           "gap_recovery": gap, "agreement_with_Bexact": agree, "mean_ms_per_shot_8proc": ms,
           "osd_fraction_min": osd, "criteria": {x: decision(x) for x in ("V3_min", "V3_lc")},
           "label": "DEVELOPMENT ONLY: already-exposed V1.5 d=3 arrays; not independent evidence"}
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: out[k] for k in ("errors_q0_q001_q002", "nonzero_ler", "gap_recovery", "agreement_with_Bexact",
                                          "criteria", "mean_ms_per_shot_8proc", "osd_fraction_min")}, indent=1))
    for k, v in contrasts.items():
        print(k, "%+.5f" % v["nonzero_estimate"], [round(c, 5) for c in v["nonzero_95ci"]], "q0 %+.5f" % v["q0_estimate"])


if __name__ == "__main__":
    main()
