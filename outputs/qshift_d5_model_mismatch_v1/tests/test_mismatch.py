"""Mismatch-study unit tests. Tiny samples on literal test seeds only (not study data)."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import mm_contract as K  # noqa: E402
import job as J  # noqa: E402
import seeds as S  # noqa: E402
import c_job  # noqa: E402


def _skeleton(circ):
    return [(ins.name, tuple(str(t) for t in ins.targets_copy())) for ins in circ.flattened()]


def test_nominal_sampler_matches_phase_c():
    for q in K.QS:
        a = J.sample(K.NOMINAL_SPEC, q, K.SUPPORT, 300, 9_001)
        b = c_job.sample("rehearsal", q, K.SUPPORT, 300, 9_001)
        assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


def test_decoders_are_phase_c():
    assert J.decode_all is c_job.decode_all
    assert K.tau() == K.C.tau() and abs(K.tau() - 1561.218) < 1e-3


def test_true_specs_change_only_noise():
    nom = K.m.build_candidate_circuit(K.NOMINAL_SPEC, 0.01, K.SUPPORT)
    nom_dem = nom.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
    for c, spec in K.TRUE_SPECS.items():
        circ = K.m.build_candidate_circuit(spec, 0.01, K.SUPPORT)
        assert _skeleton(circ) == _skeleton(nom), c
        assert str(circ) != str(nom), c
        dem = circ.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
        assert dem.num_detectors == nom_dem.num_detectors and str(dem) != str(nom_dem), c


def test_learn_recovers_known_support_on_nominal_data():
    classes, learner = J.nominal_learner()
    dets, labx, laby = [], [], []
    for qi, q in enumerate(K.QS):
        x, y = J.sample(K.NOMINAL_SPEC, q, K.SUPPORT, K.DET_PER_Q + K.LAB_PER_Q, 4_242 + qi)
        dets.append(x[: K.DET_PER_Q]); labx.append(x[K.DET_PER_Q:]); laby.append(y[K.DET_PER_Q:])
    rec = J.learn(classes, learner, dets, labx, laby)
    assert rec["learned_correct"] and tuple(rec["learned_support"]) == K.SUPPORT


def test_seed_file_collision_free():
    rec = json.loads((ROOT / "SEEDS.json").read_text(encoding="utf-8"))
    screened, _ = S.screened_values()
    vals = [v for name in S.NAMESPACES for v in rec[name].values()]
    assert len(vals) == len(set(vals)) and not set(vals) & screened
    for name in S.NAMESPACES:
        assert sorted(rec[name]) == sorted(S.keys_for(name))


def test_diag_pool_functions_smoke(tmp_path, monkeypatch):
    import diag as D
    monkeypatch.setattr(D, "RES", tmp_path / "res")
    monkeypatch.setattr(D, "ARR", tmp_path / "arr")
    (tmp_path / "res" / "pools").mkdir(parents=True)
    (tmp_path / "arr").mkdir()
    D._init()
    D._S["seeds"] = {k: 70_000 + i for i, k in enumerate(K.diag_keys())}   # literal test seeds, not study seeds
    D.burst_pool("Mz", 0)
    D.q0_pool("Mhi", 0)
    b = json.loads((tmp_path / "res" / "pools" / "Mz_burst00.json").read_text(encoding="utf-8"))
    z = json.loads((tmp_path / "res" / "pools" / "Mhi_q000.json").read_text(encoding="utf-8"))
    assert set(b) >= {"selection", "flip", "learned_support", "class_correct", "learned_correct", "seeds"}
    assert set(z["residuals"]) == {"mean_y", "mean_abs_z", "mean_z", "frac_y_negative"} and "no_burst" in z
    try:
        D.q0_pool("Mhi", 0)
        raise AssertionError("second write allowed")
    except SystemExit:
        pass
