"""DB2 design feasibility: expected errors per episode (24,000 scored rows) for candidate risk gates, from DB1's
TRAINING.json risk table only. No validation data of any study is read.

Idealisation: the bank identifies the true state of block t-1 exactly at block t (the causal one-block lag);
block 0 uses the static key A. Columns: errors / key switches over the scored blocks.

  python design_feasibility.py [TRAINING.json]
"""
import json
import sys
from pathlib import Path

TRAIN = Path(sys.argv[1]) if __name__ == "__main__" and len(sys.argv) > 1 else \
    Path(__file__).resolve().parent.parent / "qshift_decoder_bank_v1" / "TRAINING.json"
R = json.loads(TRAIN.read_text(encoding="utf-8"))["risk"]
ST = list(R)
N, SC = 1000, range(6, 30)
S = {"C0": ["A"] * 30, "N_OFF": ["OFF"] * 30, "N_C": ["C"] * 30,
     "R": ["OFF"] * 6 + ["A"] * 4 + ["OFF"] * 5 + ["A"] * 4 + ["OFF"] * 11,
     "R_long": ["OFF"] * 6 + ["A"] * 5 + ["OFF"] * 19,
     "RB": ["OFF"] * 6 + ["B"] * 4 + ["OFF"] * 5 + ["B"] * 4 + ["OFF"] * 11,
     "RX": ["OFF"] * 6 + ["A"] * 4 + ["OFF"] * 4 + ["B"] * 4 + ["OFF"] * 4 + ["A"] * 4 + ["OFF"] * 4,
     "S1": ["A"] * 15 + ["B"] * 15, "S4": ["B"] * 10 + ["C"] * 10 + ["D"] * 10}


def cost(st, ks):
    return sum(R[st[t]][ks[t]] * N for t in SC)


def switches(ks):
    return sum(ks[t] != ks[t - 1] for t in SC if t > SC[0])


def policy(st, mode, kappa, first=1, alpha=0.25, a0=1.0, b0=29.0):
    """mode: 'bank' (DB1, h = 0), 'worst' (approved DB2 rule, now arm DB2_PLAN), 'mix' (learned-destination
    mixture), 'hybrid' (amended DB2: worst case until a change out of the current state has been seen, then the
    learned mixture).
    first: the first block at which occupancy is counted (1 = from the start, 6 = from the first decision)."""
    ks, prev = ["A"], "A"
    for t in range(1, 30):
        seen = st[:t]
        cur = seen[-1]
        occ = sum(1 for i in range(max(first, 1), t) if seen[i - 1] == cur)
        lv = sum(1 for i in range(1, t) if seen[i - 1] == cur and seen[i] != cur)
        h = 0.0 if mode == "bank" else (a0 + lv) / (a0 + b0 + occ)
        outs = [seen[i] for i in range(1, t) if seen[i - 1] == cur and seen[i] != cur]
        if mode == "mix" or (mode == "hybrid" and outs):
            cnt = {d: alpha + sum(1 for i in range(1, t) if seen[i - 1] == cur and seen[i] == d) for d in ST if d != cur}
            z = sum(cnt.values())
            nxt = {k: sum(c / z * R[d][k] for d, c in cnt.items()) for k in ST}
        else:
            nxt = {k: max(R[d][k] for d in ST if d != cur) for k in ST}
        rk = {k: (1 - h) * R[cur][k] + h * nxt[k] for k in ST}
        best = min(ST, key=lambda k: (rk[k], ST.index(k)))
        k = prev if rk[prev] <= rk[best] + kappa else best
        ks.append(k)
        prev = k
    return ks


COLS = (("BANK", "bank", 0.0005, 1), ("DB2_PLAN", "worst", 0.0005, 6), ("worst k=0", "worst", 0.0, 6),
        ("MIX k=0", "mix", 0.0, 6), ("DB2 (amended)", "hybrid", 0.0, 6))

if __name__ == "__main__":
    print(f"{'panel':7s} {'ORACLE':>7s} {'STATIC':>7s} " + " ".join(f"{c[0]:>16s}" for c in COLS))
    for s, st in S.items():
        row = [f"{cost(st, st):7.1f}", f"{cost(st, ['A'] * 30):7.1f}"]
        for _, mode, kap, first in COLS:
            ks = policy(st, mode, kap, first)
            row.append(f"{cost(st, ks):10.1f} /{switches(ks):2d}  ")
        print(f"{s:7s} " + " ".join(row))
    w = max(R[d]["A"] for d in ST if d != "OFF")
    o = max(R[d]["OFF"] for d in ST if d != "OFF")
    dO = R["OFF"]["A"] - R["OFF"]["OFF"]
    print("break-even hazard OFF (worst case):", round(dO / (dO + o - w), 5))
