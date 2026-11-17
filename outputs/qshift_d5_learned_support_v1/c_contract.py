"""Phase C frozen constants (PHASE_C_PROTOCOL.md). No sampling here."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import contract as B

ROOT = Path(__file__).resolve().parent
SPEC = B.SPEC                                   # d=5, p=0.003, 5 rounds
QS = B.QS
CONDITIONS = ("K", "H")
KNOWN_SUPPORT = B.BURSTS["SC"]                  # (23, 31, 34): scaled_v1, the Phase 2 burst
SURROGATE_H = B.BURSTS["M0"]                    # stands in for H in fake/rehearsal modes ONLY

L2 = B.LD.L2
L2_PRIOR = 0.01                                 # Phase 2 Step 0 static prior
ASTAR_Q_DEC, ASTAR_CORRELATIONS = 0.0025, True  # Phase 2 Phase-1 selection (d=5 Phase 2 contract.ASTAR_Q_DEC)
ARMS = ("L2L", "L2s", "Astar", "Astar_L", "A_nominal")
CANDIDATE, COMPARATOR = "L2L", "Astar"
CONTRASTS = (("L2L", "Astar"), ("L2L", "L2s"), ("L2L", "Astar_L"), ("L2s", "Astar"), ("L2L", "A_nominal"))
NONINFERIORITY_RELATIVE_MARGIN = 0.25          # L2L - L2s upper 95% CI < 0.25 * LER(L2s)
SAFETY_RELATIVE_MARGIN = 0.05
BOOTSTRAPS = 20_000
QUANTILE_METHOD = "linear"
ALPHA_BONFERRONI = 0.05 / 2

CAL_DET_PER_Q, CAL_LAB_PER_Q = B.DET_PER_Q, B.LAB_PER_Q   # 4,000 + 500 per q (one sampler call per q)


@dataclass(frozen=True)
class Allocation:
    roots_per_q: int
    shots_per_root: int

    @property
    def jobs(self) -> int:
        return self.roots_per_q * len(QS) * len(CONDITIONS)

    def as_dict(self) -> dict:
        return asdict(self)


FROZEN = Allocation(24, 8_334)          # 200,016 per (condition, q); 1,200,096 total
REHEARSAL = Allocation(1, 1_000)
FAKE = Allocation(24, 30)
MODES = {"eval": FROZEN, "rehearsal": REHEARSAL, "fake": FAKE}


def root_key(cond, qi, r):
    return f"d5ls:C:eval:{cond}:q{QS[qi]:.2f}:root{r}"


def cal_key(cond, qi):
    return f"d5ls:C:cal:{cond}:q{QS[qi]:.2f}"


def stats_keys(cond):
    return f"d5ls:C:stats:{cond}:nonzero", f"d5ls:C:stats:{cond}:zero"


def stem(cond, qi, r):
    return f"{cond}_q{qi}_r{r:02d}"


def jobs(alloc):
    return [(c, qi, r) for c in CONDITIONS for qi in range(len(QS)) for r in range(alloc.roots_per_q)]


def all_seed_keys(alloc):
    return [root_key(*j) for j in jobs(alloc)] + [cal_key(c, qi) for c in CONDITIONS for qi in range(len(QS))] + \
           [k for c in CONDITIONS for k in stats_keys(c)]


def tau() -> float:
    rec = json.loads((ROOT / "NULL_THRESHOLD.json").read_text(encoding="utf-8"))
    if rec["mode"] != "dev" or not rec["viable"]:
        raise SystemExit("NULL_THRESHOLD.json is not a viable dev calibration")
    return float(rec["tau"])


def open_hidden_seal() -> tuple[int, ...]:
    """Open H's sealed plaintext and verify it against the committed hash. Eval mode only."""
    import c_seal
    commit = json.loads(c_seal.COMMITMENT.read_text(encoding="utf-8"))
    plain = json.loads(c_seal.SEALED.read_text(encoding="utf-8"))
    if hashlib.sha256(c_seal.canonical(plain)).hexdigest() != commit["sha256_of_canonical_plaintext"]:
        raise SystemExit("sealed plaintext does not match the committed hash")
    sup = tuple(plain["support"])
    if sup not in c_seal.candidate_pool():
        raise SystemExit("sealed support outside the committed candidate pool")
    return sup


def true_support(cond: str, mode: str, hidden_authorized: bool = False) -> tuple[int, ...]:
    if cond == "K":
        return KNOWN_SUPPORT
    if mode != "eval":
        return SURROGATE_H
    if not hidden_authorized:
        raise SystemExit("H in eval mode needs --open-hidden-seal (owner authorization)")
    return open_hidden_seal()
