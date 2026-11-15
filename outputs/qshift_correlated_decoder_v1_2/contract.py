"""Single source of truth for every name shared by the V1.2 runner and analyzer.

V1.1 failed finalization because the runner and analyzer spelled one metadata key
differently. In V1.2 both sides import these constants; no shared key is written
as a duplicated string literal.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

QS = (0.0, 0.01, 0.02)
NONZERO_QS = (0.01, 0.02)

# Arm order is also the archive member order: pred_<arm>.
ARMS = ("A0", "A", "Astar", "A2", "Bstatic", "B", "C")
ARM_DESCRIPTIONS = {
    "A0": "PyMatching at q=0 (nominal; Stage 5-style comparator; informational)",
    "A": "PyMatching at the pooled V1.2 calibration q-hat (V1.1 definition; continuity)",
    "Astar": "PyMatching at the static q selected on the V1.1 selection set (strong static baseline)",
    "A2": "PyMatching at the per-root calibration q-hat (adaptive matching)",
    "Bstatic": "five-factor enumeration at the static q selected on the V1.1 selection set",
    "B": "five-factor enumeration at the per-root calibration q-hat (candidate)",
    "C": "five-factor enumeration at the true simulated q (privileged; not deployable)",
}

CO_PRIMARY = (("B", "Astar"), ("B", "A2"))
SAFETY = ("B", "Astar")
SECONDARY = (("Bstatic", "Astar"), ("B", "Bstatic"), ("B", "A0"), ("B", "A"), ("C", "B"))

BOOTSTRAPS = 20000
QUANTILE_METHOD = "linear"
Q0_HARM_TOLERANCE = 0.0005
MIN_ASTAR_NONZERO_ERRORS = 100

DETECTORS = 40

# models_frozen.json keys (written by the runner, required by the analyzer).
KEY_SCHEMA = "schema"
KEY_POOLED_QHAT = "A_pooled_qhat"
KEY_ASTAR_Q = "Astar_static_q"
KEY_BSTATIC_Q = "Bstatic_static_q"
KEY_ROOT_QHAT = "root_qhat"
KEY_TRUE_Q = "C_true_q_by_condition"
KEY_SELECTION_SHA = "static_selection_sha256"
MODEL_REQUIRED_KEYS = (KEY_POOLED_QHAT, KEY_ASTAR_Q, KEY_BSTATIC_Q, KEY_ROOT_QHAT, KEY_TRUE_Q,
                       KEY_SELECTION_SHA)

# calibration_diagnostics.json keys.
KEY_ESTIMATION_SUMMARY = "estimation_summary"
KEY_ORDER_GATE = "condition_order_gate_passed"

# status.json states and fields.
STATE_RUNNING = "running"
STATE_READY_FOR_ANALYSIS = "evaluation_complete_pending_independent_analysis"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"
KEY_ALLOCATION = "allocation"

# Run-directory file names.
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
