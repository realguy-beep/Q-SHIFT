"""Single source of truth for every name shared by the V1.5 runner and analyzer."""
from __future__ import annotations

from dataclasses import asdict, dataclass

QS = (0.0, 0.01, 0.02)
NONZERO_QS = (0.01, 0.02)

ARMS = ("Astar", "A2sw", "Boff", "BoffStatic", "Bexact")
ARM_DESCRIPTIONS = {
    "Astar": "static correlated PyMatching, q=0.00375 (V1.3 selection; strongest static matcher)",
    "A2sw": "mode-switching adaptive PyMatching, tau=0.0005 (V1.3 selection)",
    "Boff": "V1.3 cost-consistent five-factor decoder, per-root q-hat",
    "BoffStatic": "V1.3 cost-consistent five-factor decoder, static q=0.01125 (best V1.3 decoder)",
    "Bexact": "exact DEM logical-class (maximum-likelihood) decoder at per-root detector-only q-hat (candidate; V1.4B)",
}

CANDIDATE = "Bexact"
REFERENCE = "BoffStatic"          # best V1.3 decoder
STATIC_COMPARATOR = "Astar"       # strongest static matcher
CO_PRIMARY = ((CANDIDATE, REFERENCE), (CANDIDATE, STATIC_COMPARATOR))
SAFETY = (CANDIDATE, REFERENCE)
SECONDARY = (("Bexact", "Boff"), ("Bexact", "A2sw"), ("BoffStatic", "Astar"), ("Boff", "Astar"))

BOOTSTRAPS = 20000
QUANTILE_METHOD = "linear"
Q0_HARM_TOLERANCE = 0.0005
MIN_REFERENCE_NONZERO_ERRORS = 100
TARGET_RELATIVE_REDUCTION_LOWER_BOUND = 0.10   # vs REFERENCE, 95% lower bound
DETECTORS = 40

# models_frozen.json keys.
KEY_SCHEMA = "schema"
KEY_ASTAR = "Astar_static"
KEY_TAU = "A2sw_tau"
KEY_BOFFSTATIC_Q = "BoffStatic_static_q"
KEY_ROOT_QHAT = "root_qhat"
KEY_SELECTION_SHA = "v1_3_selection_sha256"
KEY_EXACT_WIDTH = "Bexact_max_elimination_width"
MODEL_REQUIRED_KEYS = (KEY_ASTAR, KEY_TAU, KEY_BOFFSTATIC_Q, KEY_ROOT_QHAT, KEY_SELECTION_SHA, KEY_EXACT_WIDTH)

# V1.3 STATIC_SELECTION.json "selected" keys (read-only input).
SEL_ASTAR = "Astar_static"
SEL_TAU = "A2sw_tau"
SEL_BOFFSTATIC_Q = "BoffStatic_static_q"

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
