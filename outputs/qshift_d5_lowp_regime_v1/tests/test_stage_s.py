"""Stage S unit tests (no study sampling)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO))
import contract as K  # noqa: E402
import dev_aggregate as A  # noqa: E402
import prepare_dev_seeds as S  # noqa: E402


def test_conditions_and_specs():
    assert K.CONDITIONS == {"L10": ("scaled_v1", 0.001), "L15": ("scaled_v1", 0.0015)}
    for c, (_, p) in K.CONDITIONS.items():
        spec, qubits = K.spec(c)
        assert (spec.distance, spec.gate_p, spec.measurement_p, spec.regime) == (5, p, p, "balanced")
        assert tuple(qubits) == (23, 31, 34)


def test_jobs_logic_identical_to_robustness():
    a = (REPO / "outputs/qshift_d5_robustness_v1/dev_jobs.py").read_text(encoding="utf-8").splitlines()[1:]
    b = (ROOT / "dev_jobs.py").read_text(encoding="utf-8").splitlines()[1:]
    assert a == b


def test_seeds_collision_free():
    rec = json.loads((ROOT / "DEV_SEEDS.json").read_text(encoding="utf-8"))
    screened, _ = S.screened_values()
    vals = list(rec["seeds"].values()) + list(rec["rehearsal_seeds"].values())
    assert len(vals) == len(set(vals)) == 12 and not set(vals) & screened
    assert sorted(rec["seeds"]) == sorted(K.dev_key(c, qi) for c in K.CONDITIONS for qi in range(3))


def test_stop_rule_and_sizing():
    assert A.decision(0.89) == "STOP" and A.decision(None) == "STOP"
    assert A.decision(0.90) == "PROCEED_TO_STAGE_E_FREEZE"
    n = A.size_per_q(2.5e-5, 1000)                    # 30 / (2 * 2.5e-5) = 600,000
    assert n == 600_000 and n % K.ROOTS_PER_Q == 0
    assert A.size_per_q(1e-3, 50_000) == 50_016       # Phase 1 formula dominates, rounded up to 24
