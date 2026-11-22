"""Load DB2/DB3/DB4 development records (never CF1, never sealed data) with W0F keys/errors per block.
W0F is recorded in DB4; for DB2/DB3 it is the exact replay (db4_core.replay, tested in DB4)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB4 = ROOT.parent / "qshift_decoder_bank_v4"
sys.path.insert(0, str(DB4))
import db4_config as C  # noqa: E402
import db4_core as F  # noqa: E402

STUDIES = {"DB2": C.DB2, "DB3": C.DB3, "DB4": DB4}
RISK = json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))["risk"]
REF = ("W0F", "W0", "BANK", "DB2", "DB2_PLAN", "AD3", "STATIC", "ORACLE")


def records():
    for st, d in STUDIES.items():
        for p in sorted((d / "results" / "dev" / "records").glob("*.json")):
            r = json.loads(p.read_text(encoding="utf-8"))
            if "W0F" not in r["blocks"][0]["keys"]:
                rp = F.replay(r, RISK, "worst", 0.0, fallback=True)
                for b, (k, x, trig) in zip(r["blocks"], rp):
                    b["keys"]["W0F"], b["errors"]["W0F"] = k, x
                    b["source"]["W0F"] = "static_fallback" if trig else "replay"
            if "W0" not in r["blocks"][0]["keys"]:          # DB2: W0 == DB2_PLAN on every DB2 block (DB3 E3)
                for b in r["blocks"]:
                    b["keys"]["W0"], b["errors"]["W0"] = b["keys"]["DB2_PLAN"], b["errors"]["DB2_PLAN"]
            r["study"] = st
            yield r


def err_of(b, key):
    """Errors of `key` on this block if some recorded arm decoded with it, else None."""
    for a in REF:
        if b["keys"].get(a) == key:
            return b["errors"][a]
    return None
