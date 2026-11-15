"""Small shared helpers for V1.2 (no sampler, no decoder construction)."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
V1_1_PACKAGE = REPO / "outputs" / "qshift_correlated_decoder_feasibility_v1_1"
CONFIG_PATH = ROOT / "config.json"


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def atomic_json(path: Path, value) -> None:
    atomic_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def atomic_npz(path: Path, **arrays) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    raw = path.read_bytes()
    return sha256_bytes(raw), len(raw)


def load_detectors_only(path: Path, expected_rows: int) -> np.ndarray:
    """Load only the `detectors` member; observables are never accessed."""
    with np.load(path, allow_pickle=False) as archive:
        x = np.asarray(archive["detectors"])
    if x.shape != (expected_rows, 40) or not np.isin(x, [0, 1]).all():
        raise ValueError(f"invalid detector array: {path}")
    return x.astype(np.uint8, copy=False)


def fit_frozen_estimator(v1_repo: Path, config: dict):
    """Refit the V1.1 estimator from V1 training detector rows; verify it is unchanged."""
    from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (
        BurstRateEstimator,
        extract_burst_events,
    )
    from outputs.qshift_correlated_decoder_v1_2.contract import QS

    run = Path(v1_repo) / "outputs/qshift_correlated_decoder_feasibility_v1/pilot_runs/attempt_001/training"
    xs, ys = [], []
    for qi, q in enumerate(QS):
        xs.append(load_detectors_only(run / f"train_q{qi}.npz", 1000))
        ys.append(np.full(1000, q, dtype=np.float64))
    estimator = BurstRateEstimator(extract_burst_events()).fit(np.vstack(xs), np.concatenate(ys))
    spec = config["estimator"]
    if (abs(estimator.slope - spec["required_slope"]) > spec["tolerance"]
            or abs(estimator.intercept - spec["required_intercept"]) > spec["tolerance"]):
        raise RuntimeError("refit estimator differs from the frozen V1.1 fit")
    return estimator
