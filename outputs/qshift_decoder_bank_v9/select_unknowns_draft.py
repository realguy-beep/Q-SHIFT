"""Draft of the PROTOCOL_DB8.md section 3 selection (analytic DEM detector rates; no sampling). Output in
SELECTION_DRAFT.txt. The build step must re-implement this as a tested script and reproduce the table exactly."""
import json, sys
from pathlib import Path
import numpy as np
V8 = Path(__file__).resolve().parents[1] / "qshift_decoder_bank_v8"
sys.path.insert(0, str(V8 / "research")); sys.path.insert(0, str(V8.parent / "qshift_decoder_bank_v6"))
import phaseb as P
import db_core as D
import mm_contract as K
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
DC = D.C
sp = DC.spec(gate_p=DC.P0, measurement_p=DC.P0)
def rates(sup):
    c = m.build_candidate_circuit(sp, DC.BURST_Q, tuple(sup))
    dem = c.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
    prod = np.ones(c.num_detectors)
    for inst in dem.flattened():
        if inst.type != "error": continue
        p = inst.args_copy()[0]
        for tg in inst.targets_copy():
            if tg.is_relative_detector_id(): prod[tg.val] *= 1 - 2 * p
    return (1 - prod) / 2
classes = K.B.load_classes()
def incat(sup):
    try: K.B.truth(classes, tuple(sup)); return True
    except Exception: return False
ADR = V8.parent / "qshift_adaptive_robust_v1"
pub = {}
for f in ("BRS_BURSTS.json", "BRT_BURSTS.json", "BRE_BURSTS.json"):
    d = json.loads((ADR / f).read_text(encoding="utf-8")); pub.update({k: (v, d["footprint"][k]) for k, v in d["V"].items()})
bank = {lab for lab in ("W01","W05","W09","W14")}
print("E", DC.UNKNOWN)
rows = []
for lab, (sup, fp) in sorted(pub.items()):
    r = rates(sup)
    lam = {s: P.kl_noncentrality(r, P.TPL[s], 2000) for s in DC.STATES}
    best = min(lam, key=lam.get)
    rows.append((lab, sup, fp, best, round(lam[best], 1), incat(sup)))
for x in sorted(rows, key=lambda x: x[4]): print(x)
print("4-qubit tests", incat([9,25,53,1]), incat([20,29,38,9]), incat([1,3]), incat([9,25]))
print("---- 4-qubit outside-catalog candidates")
excl = {"W01","W05","W09","W14","W06","W13","X13"}
qs = sorted({q for lab,(sup,fp) in pub.items() for q in sup})
found = 0
for lab in sorted(pub):
    if lab in excl: continue
    sup = pub[lab][0]
    for q in qs:
        if q in sup: continue
        s4 = sorted(sup + [q])
        if incat(s4): continue
        r = rates(s4); lam = {s: P.kl_noncentrality(r, P.TPL[s], 2000) for s in DC.STATES}
        b = min(lam, key=lam.get)
        if 60 <= lam[b] <= 140 and b != "A":
            print("U_OUT", lab, q, s4, b, round(lam[b],1)); found += 1; break
    if found: break
