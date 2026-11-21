"""E3 (PLAN_DB3.md): replay W0 on DB2's 23 development records and score it with DB2's own F1-F6 code.
No sampling. Validation first: the same replay must reproduce DB2's and DB2_PLAN's recorded keys on every block.

  python w0_replay.py      # writes W0_REPLAY.json (once)
"""
from __future__ import annotations

import json

import numpy as np

import db3_config as C  # noqa: I001  (puts DB2 on sys.path first)
import db2_run as R2  # noqa: E402
import db3_core as K  # noqa: E402

REC = C.DB2 / "results" / "dev" / "records"


def load():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(REC.glob("*.json"))]


def criteria_for(recs, arm_keys, unknown_as):
    """Build DB2's analysis inputs with `arm_keys` ({record name: [(key, err)]}) in the DB2 slot; run R2._criteria."""
    n_rows = len(C2.SCORED) * C2.EVAL_PER_BLOCK
    S = {}
    for s in C2.SCHEDULES:
        rr = sorted([r for r in recs if r["schedule"] == s], key=lambda r: r["episode"])
        tot = {a: [sum(b["errors"][a] for b in r["blocks"]) for r in rr] for a in ("BANK", "STATIC", "AD3")}
        tot["DB2"] = [sum(unknown_as(r, i) if e is None else e for i, (_, e) in enumerate(arm_keys[f"{s}_e{r['episode']}"]))
                      for r in rr]
        sw = [sum(ks[i][0] != ks[i - 1][0] for i in range(1, len(ks))) for ks in
              (arm_keys[f"{s}_e{r['episode']}"] for r in rr)]
        res = {"episodes": len(rr), "eval_per_block": C2.EVAL_PER_BLOCK,
               "errors": {a: int(sum(v)) for a, v in tot.items()},
               "ler": {a: sum(v) / (len(rr) * n_rows) for a, v in tot.items()},
               "key_switches_per_episode": {"DB2": sw}}
        for b in ("BANK", "STATIC", "AD3"):
            d = np.array(tot["DB2"], float) - np.array(tot[b], float)
            res[f"DB2_minus_{b}"] = {"estimate": float((d / n_rows).mean()), "episodes_le_0": int((d <= 0).sum())}
        S[s] = res
    return R2._criteria({"schedules": S})


C2 = C.C2


def main():
    out_p = C.ROOT / "W0_REPLAY.json"
    if out_p.exists():
        raise SystemExit("W0_REPLAY.json exists")
    risk = json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))["risk"]
    recs = load()
    if len(recs) != 23:
        raise SystemExit("expected 23 DB2 records")
    check = {}
    for arm, (mode, kap) in (("DB2", ("hybrid", C2.KAPPA_DB2)), ("DB2_PLAN", ("worst", C2.KAPPA_PLAN))):
        check[arm] = all([k for k, _ in K.replay(r, risk, mode, kap)] == [b["keys"][arm] for b in r["blocks"]]
                         for r in recs)
    if not all(check.values()):
        raise SystemExit(f"replay does not reproduce DB2's recorded keys: {check}")
    w0 = {f"{r['schedule']}_e{r['episode']}": K.replay(r, risk, *C.CANDIDATES["W0"]) for r in recs}
    unknown = {k: [r_b for r_b, (_, e) in zip(range(6, 30), v) if e is None] for k, v in w0.items()}
    n_unknown = sum(len(v) for v in unknown.values())
    by = {f"{r['schedule']}_e{r['episode']}": r for r in recs}
    lo = criteria_for(recs, w0, lambda r, i: 0)                                    # unknown blocks: 0 errors
    hi = criteria_for(recs, w0, lambda r, i: max(r["blocks"][i]["errors"].values()))  # unknown: worst arm's errors
    own = criteria_for(recs, {k: [(b["keys"]["DB2"], b["errors"]["DB2"]) for b in by[k]["blocks"]] for k in by},
                       lambda r, i: 0)
    ref = json.loads((C.DB2 / "results" / "dev" / "ANALYSIS.json").read_text(encoding="utf-8"))["criteria"]
    if own != ref:
        raise SystemExit("criteria rebuild does not reproduce DB2's ANALYSIS criteria")
    plan = criteria_for(recs, {k: [(b["keys"]["DB2_PLAN"], b["errors"]["DB2_PLAN"]) for b in by[k]["blocks"]] for k in by},
                        lambda r, i: 0)
    diff_vs = {nm: {k: [(b, kw, by[k]["blocks"][i]["keys"][nm]) for i, ((kw, _), b) in enumerate(zip(v, range(6, 30)))
                        if kw != by[k]["blocks"][i]["keys"][nm]] for k, v in w0.items()}
               for nm in ("DB2", "DB2_PLAN")}
    per = {k: {"W0": sum(e or 0 for _, e in v), "DB2": sum(b["errors"]["DB2"] for b in by[k]["blocks"]),
               "DB2_PLAN": sum(b["errors"]["DB2_PLAN"] for b in by[k]["blocks"])} for k, v in w0.items()}
    res = {"schema": "qshift-decoder-bank-db3-w0-replay-v1",
           "source": "outputs/qshift_decoder_bank_v2/results/dev/records (23 DB2 development episodes)",
           "replay_reproduces_recorded_keys": check, "criteria_rebuild_reproduces_DB2": True,
           "unknown_blocks": n_unknown, "unknown": {k: v for k, v in unknown.items() if v},
           "criteria_unknown_as_0": lo, "criteria_unknown_as_worst_arm": hi,
           "criteria_DB2_PLAN": plan,
           "E3": {"W0": bool(lo["ADVANCE"] and hi["ADVANCE"]), "DB2_PLAN": bool(plan["ADVANCE"]),
                  "DB2": bool(own["ADVANCE"])},
           "errors_per_episode": per,
           "blocks_where_W0_differs": {nm: {k: v for k, v in d.items() if v} for nm, d in diff_vs.items()}}
    import studykit as SK
    SK.write_once_json(out_p, res)
    print(json.dumps({"check": check, "unknown": n_unknown, "E3": res["E3"], "values": lo["values"]}, indent=1))


if __name__ == "__main__":
    main()
