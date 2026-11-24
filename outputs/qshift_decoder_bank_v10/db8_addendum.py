"""Read-only DB8 addendum (audit F6, F10, F11): summaries PROTOCOL_DB8 promised but DB8's analyser did not print.

  python db8_addendum.py          # writes DB8_ADDENDUM.json beside this file (refuses to overwrite)
  python db8_addendum.py --check  # recomputes and compares

Input: the 64 committed DB8 records only (v9/results/dev/records). No archive, no sampling. Every record is first checked
with validate.validate_record. No gate, threshold or frozen result changes. Descriptive: no p values, no intervals."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for _p in (ROOT.parents[1], ROOT.parent / "qshift_decoder_bank_v9", ROOT):
    sys.path.insert(0, str(_p))
import db8_config as C  # noqa: E402,I001
import controller as CT  # noqa: E402
import validate as V  # noqa: E402

ARMS = ("LA_W0F", "LA_R1", "LA_R2", "LA_R2_170")


def load():
    seeds, tr, out = V.db8_seeds(), V.training(), []
    for s, n in C.EPISODES.items():
        for e in range(n):
            r = json.loads((C.ROOT / "results" / "dev" / "records" / f"{s}_e{e}.json").read_text(encoding="utf-8"))
            V.validate_record(r, seeds, tr, (s, e))
            out.append(r)
    return out


def cell():
    return {"firings": 0, "correct": 0, "saved_vs_W0F": 0}


def build(recs):
    onset, opp, near = {}, defaultdict(int), []
    unk = {a: {p: {"firings": 0, "wrong_by_block_truth": 0, "wrong_by_panel_wording": 0, "key_changing_wrong": 0}
               for p in C.U_PANELS} for a in ARMS}
    for a in ARMS:
        onset[a] = {"by_destination": {}, "non_onset": {"changed": cell(), "no_op": cell()}}
    for r in recs:
        for b in r["blocks"]:
            t = b["block"]
            is_on = r["states"][t] != r["states"][t - 1]
            opp[b["state"]] += is_on
            for a in ARMS:
                if b["source"][a] != "lookahead":
                    continue
                ok, ch = b["keys"][a] == "bank:" + b["state"], b["keys"][a] != b["keys"]["W0F"]
                box = onset[a]["by_destination"].setdefault(b["state"], {"changed": cell(), "no_op": cell()}) if is_on \
                    else onset[a]["non_onset"]
                c = box["changed" if ch else "no_op"]
                c["firings"] += 1
                c["correct"] += ok
                c["saved_vs_W0F"] += b["errors"]["W0F"] - b["errors"][a]
                if r["schedule"] in C.U_PANELS:
                    u = unk[a][r["schedule"]]
                    u["firings"] += 1
                    u["wrong_by_block_truth"] += not ok
                    u["wrong_by_panel_wording"] += 1
                    u["key_changing_wrong"] += (not ok) and ch
            if r["schedule"] == "U_NEAR" and is_on:
                near.append({"episode": r["episode"], "block": t, "alarm_g": round(b["lookahead"]["g"], 2),
                             "fit_B": round(b["db8"]["gf1"]["B"], 3), "keys": {a: b["keys"][a] for a in ("W0F", "LA_R1", "LA_R2", "LA_R2_170")},
                             "excess_vs_W0F": {a: b["errors"][a] - b["errors"]["W0F"] for a in ("LA_R1", "LA_R2", "LA_R2_170")}})
    for a in ARMS:
        onset[a]["by_destination"] = dict(sorted(onset[a]["by_destination"].items()))
    return {"schema": "qshift-decoder-bank-v10-db8-addendum-v1", "status": "descriptive; DB8 NO ADVANCE unchanged",
            "onset_opportunities": dict(sorted((k, v) for k, v in opp.items() if v)), "onset_table": onset,
            "unknown_panels": unk, "U_NEAR_onsets": near, "cb_memory_sensitivity": cb_replay(recs)}


def cb_replay(recs):
    """Pooled CB errors and keys under each memory rule, from the FIX arms' recorded errors (F6)."""
    tr = V.training()
    out = {}
    for mem in CT.MEMORIES:
        tot = diff = 0
        for r in recs:
            prev = r["static_key"]
            for b in r["blocks"]:
                k, src, prev = CT.cb_key(b["db8"]["gf1"], tr["tau_fit"], tr["risk"], prev, b["keys"]["W0F"], memory=mem)
                tot += b["errors"]["W0F"] if src == "w0f" else b["errors"]["FIX_" + k[5:]]
                diff += k != b["keys"]["CB"]
        out[mem] = {"pooled_errors": tot, "keys_different_from_frozen": diff}
    return out


def main(argv):
    res = json.dumps(build(load()), indent=1, sort_keys=True) + "\n"
    p = ROOT / "DB8_ADDENDUM.json"
    if "--check" in argv:
        if p.read_bytes() != res.encode():
            raise SystemExit("DB8_ADDENDUM.json does not reproduce")
        print("reproduces")
        return
    with open(p, "x", encoding="utf-8", newline="\n") as f:
        f.write(res)


if __name__ == "__main__":
    main(sys.argv[1:])
