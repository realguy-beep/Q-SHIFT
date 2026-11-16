"""Draw and seal V1.6's hidden second burst BEFORE any learner development.

Draws one support uniformly at random (OS entropy) from the detectable 1-3 data-qubit
X-burst supports at d=3, excluding the known burst (8, 12, 15). Writes the plaintext
(support + random salt) ONLY to a sealed file outside the git worktree, and writes the
SHA-256 commitment of the canonical plaintext into HIDDEN_BURST_COMMITMENT.json for git.
Nothing about the drawn support is printed. Refuses to run twice.

The plaintext is opened only inside the frozen V1.6 run, which must verify the hash.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402

COMMITMENT = ROOT / "HIDDEN_BURST_COMMITMENT.json"
SEALED = ROOT.parents[2].parent / "qshift_v1_6_hidden_burst_SEALED.json"  # outside the worktree
KNOWN = (8, 12, 15)


def detectable_supports() -> list[tuple[int, ...]]:
    spec = m.CodeSpec()
    data = sorted(m.data_qubit_grid(spec).values())
    out = []
    for k in (1, 2, 3):
        for sub in itertools.combinations(data, k):
            try:
                m.extract_burst_events(spec, sub)
            except RuntimeError:
                continue
            out.append(sub)
    return out


def canonical(plaintext: dict) -> bytes:
    return json.dumps(plaintext, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> None:
    if COMMITMENT.exists() or SEALED.exists():
        raise SystemExit("hidden burst already sealed; refusing to redraw")
    pool = [s for s in detectable_supports() if s != KNOWN]
    if len(pool) != 118:
        raise RuntimeError(f"unexpected candidate pool size {len(pool)}")
    support = pool[secrets.randbelow(len(pool))]
    plaintext = {"support": list(support), "salt": secrets.token_hex(32),
                 "schema": "qshift-v1.6-hidden-burst-plaintext-v1"}
    SEALED.write_text(json.dumps(plaintext, indent=2) + "\n", encoding="utf-8", newline="\n")
    COMMITMENT.write_text(json.dumps({
        "schema": "qshift-v1.6-hidden-burst-commitment-v1",
        "sha256_of_canonical_plaintext": hashlib.sha256(canonical(plaintext)).hexdigest(),
        "canonical_form": "json.dumps(plaintext, sort_keys=True, separators=(',', ':'))",
        "candidate_pool": "detectable 1-3 data-qubit X-burst supports at d=3, excluding (8, 12, 15): 118 supports",
        "draw": "uniform via secrets.randbelow (OS entropy)",
        "sealed_location": "outside git, beside the worktrees: qshift_v1_6_hidden_burst_SEALED.json",
        "rule": "plaintext not read or printed during learner development; opened only inside the frozen V1.6 run, which verifies this hash",
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("sealed; commitment written (support not shown)")


if __name__ == "__main__":
    main()
