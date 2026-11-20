"""DEFERRED check (PLAN_RE2.md rev 2): is H3 or H4 contaminated by RE1's H2? Frozen with RE2; NOT run at build.

Runs only after the owner says "Open the RE1 seal", and only with --owner-opened-re1-seal. It opens both seals,
applies the frozen rule (same class as H2, or the drawn representative shares >= 2 qubits with H2) and writes only
two booleans to results/re2/CONTAMINATION.json. It prints and records no support.

Pre-declared consequence: a contaminated burst's conditions (H3: G3, G4; H4: G5) stay reported but are relabelled
"not independent of RE1"; its confirmatory claim is withdrawn and the verdict is restated without those conditions.
"""
from __future__ import annotations

import argparse
import json
from multiprocessing import get_context

import re2_config as C

OUT = C.ROOT / "results" / "re2" / "CONTAMINATION.json"
AFFECTED = {"H3": ["G3", "G4"], "H4": ["G5"]}


def _check():
    import mm_contract as K
    import re1_seal
    import re2_seal
    cl = K.B.load_classes()
    h2 = re1_seal.open_seal()
    hid = re2_seal.open_seal()
    c2 = K.B.truth(cl, tuple(h2))[0]
    return {h: bool(K.B.truth(cl, tuple(s))[0] == c2 or len(set(s) & set(h2)) >= 2) for h, s in hid.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner-opened-re1-seal", action="store_true")
    x = ap.parse_args()
    if not x.owner_opened_re1_seal:
        raise SystemExit("requires the owner's 'Open the RE1 seal' and --owner-opened-re1-seal")
    if OUT.exists():
        raise SystemExit("CONTAMINATION.json exists")
    with get_context("spawn").Pool(1) as pool:
        res = pool.apply(_check)
    OUT.write_text(json.dumps({"schema": "qshift-adaptive-robust-re2-contamination-v1", "contaminated": res,
                               "affected_conditions": {h: AFFECTED[h] for h, v in res.items() if v}},
                              indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(res))


if __name__ == "__main__":
    main()
