"""DB2 rule candidates, expected errors from DB1 TRAINING.json risk table only (no validation data).
Identification assumed perfect with the causal one-block lag; t=0 uses the static key."""
import json, sys
from pathlib import Path
TRAIN = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "qshift_decoder_bank_v1" / "TRAINING.json"
R = json.load(open(TRAIN))["risk"]; ST = list(R); N = 1000; SC = range(6, 30)
S = {"C0": ["A"]*30, "N_OFF": ["OFF"]*30, "N_C": ["C"]*30,
     "R": ["OFF"]*6+["A"]*4+["OFF"]*5+["A"]*4+["OFF"]*11,
     "R_long": ["OFF"]*6+["A"]*5+["OFF"]*19,
     "RB": ["OFF"]*6+["B"]*4+["OFF"]*5+["B"]*4+["OFF"]*11,
     "RX": ["OFF"]*6+["A"]*4+["OFF"]*4+["B"]*4+["OFF"]*4+["A"]*4+["OFF"]*4,
     "S1": ["A"]*15+["B"]*15, "S4": ["B"]*10+["C"]*10+["D"]*10}
cost = lambda st, ks: sum(R[st[t]][ks[t]]*N for t in SC)
def bank(st): return ["A"] + [st[t-1] if st[t] != st[t-1] else st[t] for t in range(1, 30)]
def db2(st, a0=1., b0=29., alpha=.25):
    ks = ["A"]
    for t in range(1, 30):
        seen = st[:t]; cur = seen[-1]
        occ = sum(1 for s in seen[:-1] if s == cur)           # completed blocks in cur that had a successor
        lv = sum(1 for i in range(1, t) if seen[i-1] == cur and seen[i] != cur)
        h = (a0 + lv) / (a0 + b0 + occ)                         # hazard of leaving the current state
        cnt = {d: alpha + sum(1 for i in range(1, t) if seen[i-1] == cur and seen[i] == d) for d in ST if d != cur}
        z = sum(cnt.values())
        rk = {k: (1-h)*R[cur][k] + h*sum(c/z*R[d][k] for d, c in cnt.items()) for k in ST}
        ks.append(min(ST, key=lambda k: (rk[k], ST.index(k))))
    return ks
def worst(st, a0=1., b0=29.):
    ks = ["A"]
    for t in range(1, 30):
        seen = st[:t]; cur = seen[-1]
        occ = sum(1 for x in seen[:-1] if x == cur)
        lv = sum(1 for i in range(1, t) if seen[i-1] == cur and seen[i] != cur)
        h = (a0 + lv) / (a0 + b0 + occ)
        rk = {k: (1-h)*R[cur][k] + h*max(R[d][k] for d in ST if d != cur) for k in ST}
        ks.append(min(ST, key=lambda k: (rk[k], ST.index(k))))
    return ks
print("DB2 candidate: worst-case destination")
for s, st in S.items():
    print(f" {s:6s} {cost(st, worst(st)):6.1f}", "".join(x[0] for x in worst(st)))
for alpha in (0.25, 1.0):
    print("ablation: learned-destination mixture, alpha", alpha)
    for s, st in S.items():
        k = db2(st, alpha=alpha)
        print(f" {s:6s} ORACLE {cost(st,st):6.1f} STATIC {cost(st,['A']*30):6.1f} BANK {cost(st,bank(st)):6.1f} DB2 {cost(st,k):6.1f} ", "".join(x[0] for x in k))
