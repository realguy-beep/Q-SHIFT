"""Draw and seal Phase C's hidden d=5 burst H. Nothing about the drawn support is printed.

Pool: every weight-3 support in CLASSES_D5.json, excluding all supports in the four development
classes (SC 790, CR 901, M0 213, M1 223). Uniform draw via secrets.randbelow (OS entropy).
The plaintext (support + random salt) goes ONLY to a file outside the git worktree; the SHA-256
of its canonical form goes to HIDDEN_COMMITMENT_C.json for git. Refuses to run twice.
The plaintext is opened only inside the frozen Phase C eval run, with explicit owner authorization.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

COMMITMENT = ROOT / "HIDDEN_COMMITMENT_C.json"
SEALED = ROOT.parents[2].parent / "qshift_d5_learned_support_hidden_SEALED.json"  # beside the worktrees
DEV_CLASSES = (790, 901, 213, 223)


def candidate_pool() -> list[tuple[int, ...]]:
    rec = json.loads((ROOT / "CLASSES_D5.json").read_text(encoding="utf-8"))
    pool = []
    for i, c in enumerate(rec["classes"]):
        if i in DEV_CLASSES:
            continue
        pool += [tuple(s) for s in c["flip0"] + c["flip1"] if len(s) == 3]
    return sorted(pool)


def canonical(plaintext: dict) -> bytes:
    return json.dumps(plaintext, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> None:
    if COMMITMENT.exists() or SEALED.exists():
        raise SystemExit("hidden burst already sealed; refusing to redraw")
    pool = candidate_pool()
    support = pool[secrets.randbelow(len(pool))]
    plaintext = {"support": list(support), "salt": secrets.token_hex(32),
                 "schema": "qshift-d5-learned-support-hidden-plaintext-v1"}
    SEALED.write_text(json.dumps(plaintext, indent=2) + "\n", encoding="utf-8", newline="\n")
    COMMITMENT.write_text(json.dumps({
        "schema": "qshift-d5-learned-support-hidden-commitment-v1",
        "sha256_of_canonical_plaintext": hashlib.sha256(canonical(plaintext)).hexdigest(),
        "canonical_form": "json.dumps(plaintext, sort_keys=True, separators=(',', ':'))",
        "candidate_pool": f"weight-3 supports in CLASSES_D5.json excluding classes {list(DEV_CLASSES)}: {len(pool)} supports",
        "candidate_pool_size": len(pool),
        "draw": "uniform via secrets.randbelow (OS entropy)",
        "sealed_location": "outside git, beside the worktrees: qshift_d5_learned_support_hidden_SEALED.json",
        "rule": ("plaintext not read or printed while building Phase C; opened only inside the frozen Phase C eval "
                 "run (flag --open-hidden-seal, owner-authorized), which verifies this hash"),
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"sealed; commitment written; pool {len(pool)} (support not shown)")


if __name__ == "__main__":
    main()
