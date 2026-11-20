"""Draw and seal RE2's hidden bursts H3 (footprint >= 25) and H4 (footprint <= 20). Nothing about them is printed.

Uniform draw of one class per stratum from re2_pool.pools() via secrets.randbelow; the support is the class's
representative. Plaintext (supports + salt) goes ONLY to a file outside the git worktree; its SHA-256, the pool hash
and the rules go to HIDDEN_COMMITMENT_RE2.json. Refuses to run twice. Never reads RE1's seal. Opened only inside the
frozen RE2 run (--open-hidden-seal).
"""
from __future__ import annotations

import hashlib
import json
import secrets
from multiprocessing import get_context

import re2_config as C

COMMITMENT = C.ROOT / "HIDDEN_COMMITMENT_RE2.json"
SEALED = C.ROOT.parents[2].parent / "qshift_re2_hidden_SEALED.json"     # beside the worktrees, outside git


def canonical(plain: dict) -> bytes:
    return json.dumps(plain, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _draw():
    import re2_pool as P
    el, pl = P.eligible(), P.pools()
    doc = P.pool_doc()
    plain = {"schema": "qshift-re2-hidden-plaintext-v1", "salt": secrets.token_hex(32)}
    for h in C.HIDDEN:
        ci = pl[h][secrets.randbelow(len(pl[h]))]
        plain[h] = list(el[ci][0])
    return plain, doc


def open_seal() -> dict:
    """{"H3": support, "H4": support}; verifies the commitment and pool membership. Run-time only."""
    import re2_pool as P
    commit = json.loads(COMMITMENT.read_text(encoding="utf-8"))
    plain = json.loads(SEALED.read_text(encoding="utf-8"))
    if hashlib.sha256(canonical(plain)).hexdigest() != commit["sha256_of_canonical_plaintext"]:
        raise SystemExit("sealed plaintext does not match the committed hash")
    if P.pool_doc()["pool_sha256"] != commit["pool"]["pool_sha256"]:
        raise SystemExit("pool changed since the seal")
    el, pl = P.eligible(), P.pools()
    out = {}
    for h in C.HIDDEN:
        sup = tuple(plain[h])
        if sup not in {el[ci][0] for ci in pl[h]}:
            raise SystemExit(f"{h} outside its committed pool")
        out[h] = sup
    return out


def main() -> None:
    if COMMITMENT.exists() or SEALED.exists():
        raise SystemExit("RE2 bursts already sealed; refusing to redraw")
    with get_context("spawn").Pool(1) as pool:
        plain, doc = pool.apply(_draw)
    SEALED.write_text(json.dumps(plain, indent=2) + "\n", encoding="utf-8", newline="\n")
    COMMITMENT.write_text(json.dumps({
        "schema": "qshift-re2-hidden-commitment-v1",
        "sha256_of_canonical_plaintext": hashlib.sha256(canonical(plain)).hexdigest(),
        "canonical_form": "json.dumps(plaintext, sort_keys=True, separators=(',', ':'))",
        "bursts": {"H3": "footprint >= 25 detectors", "H4": "footprint <= 20 detectors"},
        "pool": doc,
        "draw": "one class per stratum, uniform via secrets.randbelow (OS entropy); support = class representative",
        "sealed_location": "outside git, beside the worktrees: qshift_re2_hidden_SEALED.json",
        "re1_seal": "not read (owner decision 2026-11-20)",
        "rule": "not read or printed while building RE2; opened only inside the frozen RE2 run (--open-hidden-seal)",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print("sealed; pools", doc["draw_pool_sizes"], "(supports not shown)")


if __name__ == "__main__":
    main()
