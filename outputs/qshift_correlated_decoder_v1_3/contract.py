"""Single source of truth for every name shared by the V1.3 runner and analyzer."""
from __future__ import annotations

from dataclasses import asdict, dataclass

QS = (0.0, 0.01, 0.02)
NONZERO_QS = (0.01, 0.02)

ARMS = ("Astar", "AstarAlt", "A2sw", "B", "Bstatic", "Boff", "BoffStatic", "Coff")
ARM_DESCRIPTIONS = {
    "Astar": "best static PyMatching over {correlations ON, OFF} x q grid, selected on the V1.2 arrays (strong static baseline)",
    "AstarAlt": "best static PyMatching in the other correlation mode (reported)",
    "A2sw": "mode-switching adaptive PyMatching: OFF on the base DEM if per-root q-hat < tau, else ON at q-hat (strongest adaptive matching)",
    "B": "frozen V1.2 B: five-factor, residual correlations ON, per-root q-hat (continuity)",
    "Bstatic": "frozen V1.2 Bstatic: five-factor, residual correlations ON, q=0.0025 (continuity)",
    "Boff": "five-factor, residual correlations OFF (cost-consistent), per-root q-hat (candidate)",
    "BoffStatic": "five-factor, residual correlations OFF, static q selected on the V1.2 arrays",
    "Coff": "five-factor, residual correlations OFF, true simulated q (privileged; calibration check)",
}

CANDIDATE = "Boff"
STATIC_COMPARATOR = "Astar"
ADAPTIVE_COMPARATOR = "A2sw"
CO_PRIMARY = ((CANDIDATE, STATIC_COMPARATOR), (CANDIDATE, ADAPTIVE_COMPARATOR))
SAFETY = (CANDIDATE, ADAPTIVE_COMPARATOR)
SECONDARY = (("Boff", "B"), ("Boff", "BoffStatic"), ("Coff", "Boff"), ("A2sw", "Astar"),
             ("Boff", "AstarAlt"), ("B", "Astar"))

BOOTSTRAPS = 20000
QUANTILE_METHOD = "linear"
Q0_HARM_TOLERANCE = 0.0005
MIN_STATIC_NONZERO_ERRORS = 100
DETECTORS = 40

# Frozen V1.2 values carried as continuity arms.
V1_2_BSTATIC_Q = 0.0025

# models_frozen.json keys.
KEY_SCHEMA = "schema"
KEY_ASTAR = "Astar_static"          # {"correlations": bool, "q": float}
KEY_ASTAR_ALT = "AstarAlt_static"   # {"correlations": bool, "q": float}
KEY_TAU = "A2sw_tau"
KEY_BSTATIC_Q = "Bstatic_static_q"
KEY_BOFFSTATIC_Q = "BoffStatic_static_q"
KEY_ROOT_QHAT = "root_qhat"
KEY_TRUE_Q = "Coff_true_q_by_condition"
KEY_SELECTION_SHA = "selection_sha256"
MODEL_REQUIRED_KEYS = (KEY_ASTAR, KEY_ASTAR_ALT, KEY_TAU, KEY_BSTATIC_Q, KEY_BOFFSTATIC_Q,
                       KEY_ROOT_QHAT, KEY_TRUE_Q, KEY_SELECTION_SHA)

# STATIC_SELECTION.json "selected" keys.
SEL_ASTAR = KEY_ASTAR
SEL_ASTAR_ALT = KEY_ASTAR_ALT
SEL_TAU = KEY_TAU
SEL_BOFFSTATIC_Q = KEY_BOFFSTATIC_Q

KEY_ESTIMATION_SUMMARY = "estimation_summary"
KEY_ORDER_GATE = "condition_order_gate_passed"

STATE_RUNNING = "running"
STATE_READY_FOR_ANALYSIS = "evaluation_complete_pending_independent_analysis"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"
KEY_ALLOCATION = "allocation"

FILE_STATUS = "status.json"
FILE_IDENTITY = "execution_identity.json"
FILE_MODELS = "models_frozen.json"
FILE_CALIBRATION = "calibration_diagnostics.json"
FILE_TRAINING = "training_summary.json"
FILE_ANALYSIS = "analysis.json"
FILE_PAIRED_CSV = "paired_results.csv"
FILE_MANIFEST = "run_manifest.json"
DIR_EVALUATION = "evaluation"
DIR_CALIBRATION = "calibration"
KEY_LABELS_EXPOSED = "evaluation_labels_exposed_to_decoders"

SEED_STATS_PRIMARY = "statistics:primary-bootstrap"
SEED_STATS_ZERO = "statistics:zero-bootstrap"


@dataclass(frozen=True)
class Allocation:
    roots_per_q: int
    eval_shots_per_root: int
    calibration_shots_per_root: int

    @property
    def roots(self) -> int:
        return len(QS) * self.roots_per_q

    @property
    def eval_shots(self) -> int:
        return self.roots * self.eval_shots_per_root

    @property
    def calibration_shots(self) -> int:
        return self.roots * self.calibration_shots_per_root

    @property
    def sampler_calls(self) -> int:
        return 2 * self.roots

    def as_dict(self) -> dict:
        return asdict(self)


FROZEN_ALLOCATION = Allocation(roots_per_q=24, eval_shots_per_root=4000, calibration_shots_per_root=500)


def eval_key(q: float, root: int) -> str:
    return f"evaluation:q{q:.2f}:root{root:02d}"


def calibration_key(q: float, root: int) -> str:
    return f"calibration:q{q:.2f}:root{root:02d}"


def eval_archive_name(qi: int, root: int) -> str:
    return f"eval_q{qi}_r{root:02d}.npz"


def calibration_archive_name(qi: int, root: int) -> str:
    return f"cal_q{qi}_r{root:02d}.npz"


def root_id(qi: int, root: int) -> str:
    return f"q{qi}_r{root:02d}"


def pred_member(arm: str) -> str:
    return f"pred_{arm}"
