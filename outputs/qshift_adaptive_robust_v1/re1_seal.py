"""Draw and seal RE1's hidden burst H2. Nothing about the drawn support is printed.

Pool: weight-3 supports in CLASSES_D5.json, excluding (a) every support in the development and Phase C classes
(SC/K 790, CR 901, M0 213, M1 223, and the class containing Phase C's H), (b) any support sharing >= 2 qubits with
K, Phase C's H, M0, M1 or CR (i.e. within one qubit), and (c) the public rehearsal support.
Uniform draw via secrets.randbelow. The plaintext (support + salt) goes ONLY to a file outside the git worktree;
its SHA-256 goes to HIDDEN_COMMITMENT_RE1.json. Refuses to run twice. Opened only inside the frozen RE1 run with
the owner-authorized flag --open-hidden-seal.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path

import re1_config as R

ROOT = Path(__file__).resolve().parent
LS = R.D.OUTS / "qshift_d5_learned_support_v1"
COMMITMENT = ROOT / "HIDDEN_COMMITMENT_RE1.json"
SEALED = ROOT.parents[2].parent / "qshift_re1_hidden_SEALED.json"        # beside the worktrees, outside git
NEAR = {"K": (23, 31, 34), "PhaseC_H": (12, 34, 40), "M0": (12, 34, 45), "M1": (1, 23, 45), "CR": (25, 27, 29)}
EXCLUDED_CLASSES_BASE = (790, 901, 213, 223)


def _classes():
    return json.loads((LS / "CLASSES_D5.json").read_text(encoding="utf-8"))["classes"]


def _supports(c):
    return [tuple(s) for s in c["flip0"] + c["flip1"] if len(s) == 3]


def excluded_classes():
    cl = _classes()
    h = tuple(sorted(NEAR["PhaseC_H"]))
    hc = [i for i, c in enumerate(cl) if h in {tuple(sorted(s)) for s in _supports(c)}]
    return tuple(sorted(set(EXCLUDED_CLASSES_BASE) | set(hc)))


def base_pool():
    ex = set(excluded_classes())
    pool = []
    for i, c in enumerate(_classes()):
        if i in ex:
            continue
        for s in _supports(c):
            if all(len(set(s) & set(n)) < 2 for n in NEAR.values()):
                pool.append(tuple(s))
    return sorted(set(pool))


def rehearsal_support():
    """Public, deterministic rehearsal burst (never H2): the first eligible support."""
    return base_pool()[0]


def candidate_pool():
    reh = rehearsal_support()
    return [s for s in base_pool() if s != reh]


def canonical(plain: dict) -> bytes:
    return json.dumps(plain, sort_keys=True, separators=(",", ":")).encode("utf-8")


def open_seal() -> tuple[int, ...]:
    commit = json.loads(COMMITMENT.read_text(encoding="utf-8"))
    plain = json.loads(SEALED.read_text(encoding="utf-8"))
    if hashlib.sha256(canonical(plain)).hexdigest() != commit["sha256_of_canonical_plaintext"]:
        raise SystemExit("sealed plaintext does not match the committed hash")
    sup = tuple(plain["support"])
    if sup not in candidate_pool():
        raise SystemExit("sealed support outside the committed candidate pool")
    return sup


def main() -> None:
    if COMMITMENT.exists() or SEALED.exists():
        raise SystemExit("H2 already sealed; refusing to redraw")
    pool = candidate_pool()
    sup = pool[secrets.randbelow(len(pool))]
    plain = {"support": list(sup), "salt": secrets.token_hex(32), "schema": "qshift-re1-hidden-plaintext-v1"}
    SEALED.write_text(json.dumps(plain, indent=2) + "\n", encoding="utf-8", newline="\n")
    COMMITMENT.write_text(json.dumps({
        "schema": "qshift-re1-hidden-commitment-v1",
        "sha256_of_canonical_plaintext": hashlib.sha256(canonical(plain)).hexdigest(),
        "canonical_form": "json.dumps(plaintext, sort_keys=True, separators=(',', ':'))",
        "excluded_classes": list(excluded_classes()),
        "excluded_near_supports": {k: list(v) for k, v in NEAR.items()},
        "near_rule": "excluded if sharing >= 2 qubits with any listed support",
        "rehearsal_support_excluded": list(rehearsal_support()),
        "candidate_pool_size": len(pool),
        "draw": "uniform via secrets.randbelow (OS entropy)",
        "sealed_location": "outside git, beside the worktrees: qshift_re1_hidden_SEALED.json",
        "rule": "not read or printed while building RE1; opened only inside the frozen RE1 run (--open-hidden-seal)",
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"sealed; pool {len(pool)} (support not shown)")


if __name__ == "__main__":
    main()
