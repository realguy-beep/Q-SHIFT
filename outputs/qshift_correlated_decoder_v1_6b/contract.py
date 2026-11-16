"""Single source of truth for every name shared by the V1.6b runner and analyzer."""
from __future__ import annotations

from dataclasses import asdict, dataclass

CONDITIONS = ("known", "hidden")
QS = (0.0, 0.01, 0.02)
NONZERO_QS = (0.01, 0.02)
KNOWN_SUPPORT = (8, 12, 15)

ARMS = ("A_nominal", "Astar_oracle", "Astar_learned", "BoffStatic_oracle", "Bexact_oracle", "Blearn")
ARM_DESCRIPTIONS = {
    "A_nominal": "PyMatching on the burst-free base DEM, correlations OFF (no burst knowledge)",
    "Astar_oracle": "static correlated PyMatching, q=0.00375, TRUE burst support (oracle; strongest matcher)",
    "Astar_learned": "static correlated PyMatching, q=0.00375, LEARNED device support (base DEM if none learned)",
    "BoffStatic_oracle": "V1.3 cost-consistent five-factor, q=0.01125, TRUE burst support (oracle)",
    "Bexact_oracle": "exact DEM logical-class decoder, TRUE support, per-root q-hat (oracle-support ceiling)",
    "Blearn": "exact DEM logical-class decoder, LEARNED device support and flip, per-root q-hat (candidate)",
}
STATIC_MATCHING_Q = 0.00375   # V1.3 selection, reused unchanged
BOFFSTATIC_Q = 0.01125        # V1.3 selection, reused unchanged

CANDIDATE = "Blearn"
KNOWN_CO_PRIMARY = (("Blearn", "Astar_oracle"), ("Blearn", "Astar_learned"))
ORACLE_GAP = ("Blearn", "Bexact_oracle")
HIDDEN_NOT_WORSE = ("Blearn", "Astar_learned")
SAFETY = ("Blearn", "Astar_oracle")
TARGET = ("Blearn", "Astar_oracle")
SECONDARY = (("Blearn", "BoffStatic_oracle"), ("Blearn", "A_nominal"), ("Bexact_oracle", "Astar_oracle"),
             ("Astar_learned", "Astar_oracle"))
CONTRASTS = tuple(dict.fromkeys(KNOWN_CO_PRIMARY + (ORACLE_GAP, HIDDEN_NOT_WORSE, SAFETY) + SECONDARY))

BOOTSTRAPS = 20000
QUANTILE_METHOD = "linear"
Q0_HARM_TOLERANCE = 0.0005
NONINFERIORITY_MARGIN = 0.0005
MIN_ASTAR_ORACLE_NONZERO_ERRORS = 100
TARGET_RELATIVE_REDUCTION_LOWER_BOUND = 0.40
LEARNER_THRESHOLD_ALPHA = 0.01        # Bonferroni over the 15 classes, as pre-registered
DETECTORS = 40

STATE_RUNNING = "running"
STATE_READY_FOR_ANALYSIS = "evaluation_complete_pending_independent_analysis"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"

FILE_STATUS = "status.json"
FILE_IDENTITY = "execution_identity.json"
FILE_ANALYSIS = "analysis.json"
FILE_PAIRED_CSV = "paired_results.csv"
FILE_MANIFEST = "run_manifest.json"
FILE_DEVICE = "device_learning.json"      # per condition subdirectory
FILE_MODELS = "models_frozen.json"        # per condition subdirectory
DIR_EVALUATION = "evaluation"
DIR_CALIBRATION = "calibration"
KEY_LABELS_EXPOSED = "evaluation_labels_exposed_to_decoders"

# models_frozen.json keys (per condition).
KEY_TRUE_SUPPORT = "true_support"
KEY_LEARNED_CLASS = "learned_class_index"
KEY_LEARNED_FLIP = "learned_flip"
KEY_LEARNED_REPRESENTATIVE = "learned_representative_support"
KEY_ROOT_QHAT_LEARNED = "root_qhat_learned_class"
KEY_ROOT_QHAT_TRUE = "root_qhat_true_class"
MODEL_REQUIRED_KEYS = (KEY_TRUE_SUPPORT, KEY_LEARNED_CLASS, KEY_LEARNED_FLIP, KEY_LEARNED_REPRESENTATIVE,
                       KEY_ROOT_QHAT_LEARNED, KEY_ROOT_QHAT_TRUE)


@dataclass(frozen=True)
class Allocation:
    roots_per_q: int
    eval_shots_per_root: int
    calibration_shots_per_root: int
    device_detector_shots_per_q: int
    device_labeled_shots_per_q: int

    @property
    def roots(self) -> int:
        return len(QS) * self.roots_per_q

    @property
    def sampler_calls_per_condition(self) -> int:
        return 2 * len(QS) + 2 * self.roots

    @property
    def sampler_calls(self) -> int:
        return len(CONDITIONS) * self.sampler_calls_per_condition

    @property
    def eval_shots_per_condition(self) -> int:
        return self.roots * self.eval_shots_per_root

    @property
    def shots_per_condition(self) -> int:
        return (self.roots * (self.eval_shots_per_root + self.calibration_shots_per_root)
                + len(QS) * (self.device_detector_shots_per_q + self.device_labeled_shots_per_q))

    def as_dict(self) -> dict:
        return asdict(self)


FROZEN_ALLOCATION = Allocation(roots_per_q=24, eval_shots_per_root=4000, calibration_shots_per_root=500,
                               device_detector_shots_per_q=4000, device_labeled_shots_per_q=500)


def device_key(c: str, kind: str, q: float) -> str:
    return f"{c}:device:{kind}:q{q:.2f}"


def calibration_key(c: str, q: float, root: int) -> str:
    return f"{c}:calibration:q{q:.2f}:root{root:02d}"


def eval_key(c: str, q: float, root: int) -> str:
    return f"{c}:evaluation:q{q:.2f}:root{root:02d}"


def stats_key(c: str, kind: str) -> str:
    return f"{c}:statistics:{kind}-bootstrap"


def eval_archive_name(qi: int, root: int) -> str:
    return f"eval_q{qi}_r{root:02d}.npz"


def calibration_archive_name(qi: int, root: int) -> str:
    return f"cal_q{qi}_r{root:02d}.npz"


def root_id(qi: int, root: int) -> str:
    return f"q{qi}_r{root:02d}"


def pred_member(arm: str) -> str:
    return f"pred_{arm}"
