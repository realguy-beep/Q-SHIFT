"""Multi-distance Q-SHIFT feasibility utilities; development evidence only."""
from __future__ import annotations

import hashlib
import itertools
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import stim

PAULI_REGIMES = ("x_biased", "balanced", "z_biased")
PAULI_PAIRS = ("IX", "IY", "IZ", "XI", "XX", "XY", "XZ", "YI",
               "YX", "YY", "YZ", "ZI", "ZX", "ZY", "ZZ")
DEFAULT_BIAS_RATIO = 10.0


def native_circuit(memory: str, distance: int, gate_p: float, meas_p: float) -> stim.Circuit:
    if memory not in ("x", "z"):
        raise ValueError("memory must be x or z")
    if distance not in (3, 5, 7):
        raise ValueError("pilot supports distances 3, 5, and 7")
    return stim.Circuit.generated(
        f"surface_code:rotated_memory_{memory}", distance=distance, rounds=distance,
        after_clifford_depolarization=float(gate_p),
        before_measure_flip_probability=float(meas_p),
    )


def pauli_weights(regime: str, bias_ratio: float = DEFAULT_BIAS_RATIO) -> dict[str, float]:
    if regime == "balanced":
        return {"I": 1.0, "X": 1.0, "Y": 1.0, "Z": 1.0}
    if regime == "x_biased":
        return {"I": 1.0, "X": float(bias_ratio), "Y": 1.0, "Z": 1.0}
    if regime == "z_biased":
        return {"I": 1.0, "X": 1.0, "Y": 1.0, "Z": float(bias_ratio)}
    raise ValueError(f"unknown Pauli regime: {regime}")


def pauli_probabilities(regime: str, total_p: float, bias_ratio: float = DEFAULT_BIAS_RATIO):
    weights = pauli_weights(regime, bias_ratio)
    one_total = sum(weights[k] for k in "XYZ")
    p1 = tuple(float(total_p * weights[k] / one_total) for k in "XYZ")
    raw = np.asarray([weights[a] * weights[b] for a, b in PAULI_PAIRS], dtype=np.float64)
    p2 = total_p * raw / raw.sum()
    p2[-1] += total_p - float(p2.sum())
    return p1, tuple(float(v) for v in p2)


def pauli_circuit(memory: str, distance: int, regime: str, gate_p: float,
                  meas_p: float, bias_ratio: float = DEFAULT_BIAS_RATIO) -> stim.Circuit:
    p1, p2 = pauli_probabilities(regime, gate_p, bias_ratio)
    generated = native_circuit(memory, distance, gate_p, meas_p)
    body = str(generated)
    s1 = "PAULI_CHANNEL_1(" + ",".join(format(v, ".17g") for v in p1) + ")"
    s2 = "PAULI_CHANNEL_2(" + ",".join(format(v, ".17g") for v in p2) + ")"
    body, n1 = re.subn(r"DEPOLARIZE1\([^)]*\)", s1, body)
    body, n2 = re.subn(r"DEPOLARIZE2\([^)]*\)", s2, body)
    if n1 == 0 or n2 == 0:
        raise RuntimeError(f"missing generated Clifford noise locations: 1q={n1}, 2q={n2}")
    return stim.Circuit(body)


def detector_count(distance: int, rounds: int | None = None) -> int:
    rounds = distance if rounds is None else rounds
    return (distance * distance - 1) * rounds


def build_decoder(circuit: stim.Circuit, family: str):
    if family == "native":
        dem = circuit.detector_error_model(decompose_errors=True)
        correlations = False
    elif family == "pauli_biased":
        dem = circuit.detector_error_model(
            decompose_errors=True, approximate_disjoint_errors=True)
        correlations = True
    else:
        raise ValueError(f"unknown family {family}")
    model = pymatching.Matching.from_detector_error_model(
        dem, enable_correlations=correlations)
    if model.num_detectors != circuit.num_detectors or model.num_fault_ids != 1:
        raise RuntimeError("matching detector/logical-observable schema mismatch")
    return model, dem, correlations


def decode(model, detectors: np.ndarray, correlated: bool = False) -> np.ndarray:
    d = np.asarray(detectors, dtype=np.uint8)
    if d.ndim != 2:
        raise ValueError("detectors must be a 2D binary matrix")
    if not np.isin(d, (0, 1)).all():
        raise ValueError("detectors must contain only binary values")
    raw = model.decode_batch(d, enable_correlations=True) if correlated else model.decode_batch(d)
    pred = np.asarray(raw, dtype=np.uint8)
    if pred.ndim == 2:
        if pred.shape != (len(d), 1):
            raise ValueError(f"expected one observable prediction per shot, got {pred.shape}")
        pred = pred[:, 0]
    if pred.shape != (len(d),) or not np.isin(pred, (0, 1)).all():
        raise ValueError(f"invalid logical prediction shape or values: {pred.shape}")
    return pred.astype(bool)


def candidate_metadata(circuit: stim.Circuit, dem, model, family: str,
                       candidate: Any, correlated: bool) -> dict[str, Any]:
    cb = str(circuit).encode("utf-8")
    db = str(dem).encode("utf-8")
    edges = [
        [(-1 if u is None else int(u)), (-1 if v is None else int(v)),
         float(attrs["weight"]), sorted(int(x) for x in attrs.get("fault_ids", set()))]
        for u, v, attrs in model.edges()
    ]
    return {
        "family": family, "candidate": candidate,
        "circuit_sha256": hashlib.sha256(cb).hexdigest(),
        "dem_sha256": hashlib.sha256(db).hexdigest(),
        "detectors": int(circuit.num_detectors),
        "observables": int(circuit.num_observables),
        "matching_detectors": int(model.num_detectors),
        "matching_fault_ids": int(model.num_fault_ids),
        "edges": int(model.num_edges),
        "correlated_matching": bool(correlated),
        "edge_weights_sha256": hashlib.sha256(
            json.dumps(edges, separators=(",", ":")).encode("utf-8")).hexdigest(),
    }


def detector_profiles(samples: np.ndarray) -> np.ndarray:
    d = np.asarray(samples, dtype=np.uint8)
    return (d.sum(axis=0, dtype=np.int64) + 0.5) / (len(d) + 1.0)


def marginal_scores(detectors: np.ndarray, profiles: np.ndarray) -> np.ndarray:
    d = np.asarray(detectors, dtype=np.uint8)
    p = np.asarray(profiles, dtype=np.float64)
    if p.ndim != 2 or d.ndim != 2 or p.shape[1] != d.shape[1]:
        raise ValueError("template profile and detector dimensions do not match")
    if np.any(p <= 0) or np.any(p >= 1):
        raise ValueError("profiles must lie strictly between zero and one")
    counts = d.sum(axis=0, dtype=np.int64)
    return (counts * np.log(p) + (len(d) - counts) * np.log1p(-p)).sum(axis=1)


def fit_detector_model(detectors: np.ndarray, profiles: np.ndarray) -> int:
    # np.argmax deterministically resolves exact ties to the lowest bank index.
    return int(np.argmax(marginal_scores(detectors, profiles)))


def residual_errors(labels: np.ndarray, predictions: np.ndarray) -> np.ndarray:
    y = np.asarray(labels, dtype=np.uint8)
    p = np.asarray(predictions, dtype=np.uint8)
    if y.ndim != 1 or p.ndim != 2 or p.shape[1] != len(y):
        raise ValueError("expected labels (shots,) and predictions (candidates, shots)")
    if not np.isin(y, (0, 1)).all() or not np.isin(p, (0, 1)).all():
        raise ValueError("labels and predictions must be binary")
    return np.bitwise_xor(p, y[None, :])


def select_calibration(cal_by_regime: dict[str, list[dict[str, Any]]],
                       regimes: list[str], candidate_count: int):
    rates: dict[str, list[float]] = {}
    counts: dict[str, list[int]] = {}
    shots: dict[str, int] = {}
    for regime in regimes:
        rs = cal_by_regime[regime]
        total_errors = np.zeros(candidate_count, dtype=np.int64)
        n = 0
        for row in rs:
            total_errors += row["residuals"].sum(axis=1, dtype=np.int64)
            n += row["residuals"].shape[1]
        counts[regime] = total_errors.tolist()
        rates[regime] = (total_errors / n).tolist()
        shots[regime] = n
    pooled = np.mean(np.asarray([rates[r] for r in regimes]), axis=0)
    pooled_choice = int(np.argmin(pooled))
    specialist = {r: int(np.argmin(rates[r])) for r in regimes}
    return {
        "calibration_ler": rates,
        "calibration_errors": counts,
        "calibration_shots": shots,
        "pooled_ler": pooled.tolist(),
        "pooled_fixed_index": pooled_choice,
        "regime_specialist_indices": specialist,
        "tie_break": "lowest candidate index",
    }


def bootstrap_choice_probabilities(cal_by_regime: dict[str, list[dict[str, Any]]],
                                   regimes: list[str], candidate_count: int,
                                   draws: int, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    per_regime = {r: np.stack([
        row["residuals"].sum(axis=1) / row["residuals"].shape[1]
        for row in cal_by_regime[r]
    ]) for r in regimes}
    frequencies = {r: np.zeros(candidate_count, dtype=np.int64) for r in regimes}
    pooled_freq = np.zeros(candidate_count, dtype=np.int64)
    for _ in range(draws):
        rates = {}
        for r in regimes:
            arr = per_regime[r]
            idx = rng.integers(0, len(arr), size=len(arr))
            rates[r] = arr[idx].mean(axis=0)
            frequencies[r][int(np.argmin(rates[r]))] += 1
        pooled = np.mean(np.stack([rates[r] for r in regimes]), axis=0)
        pooled_freq[int(np.argmin(pooled))] += 1
    return {
        "draws": draws,
        "seed": seed,
        "pooled_choice_probability": (pooled_freq / draws).tolist(),
        "regime_choice_probability": {
            r: (frequencies[r] / draws).tolist() for r in regimes
        },
    }


def paired_root_effect(eval_by_regime: dict[str, list[dict[str, Any]]],
                       regime: str, specialist_index: int, pooled_index: int,
                       draws: int, seed: int) -> dict[str, Any]:
    rows = eval_by_regime[regime]
    diffs = []
    cand_errors = base_errors = n_total = 0
    cand_only = base_only = pred_disagree = 0
    for row in rows:
        resid = row["residuals"]
        cand = resid[specialist_index]
        base = resid[pooled_index]
        n = resid.shape[1]
        diffs.append(float(cand.mean() - base.mean()))
        cand_errors += int(cand.sum())
        base_errors += int(base.sum())
        n_total += n
        cand_only += int(np.count_nonzero(cand & ~base))
        base_only += int(np.count_nonzero(~cand & base))
        pred_disagree += int(np.count_nonzero(
            row["predictions"][specialist_index] != row["predictions"][pooled_index]))
    arr = np.asarray(diffs, dtype=np.float64)
    rng = np.random.default_rng(seed)
    boot_idx = rng.integers(0, len(arr), size=(draws, len(arr)))
    boot = arr[boot_idx].mean(axis=1)
    mean_diff = float(arr.mean())
    return {
        "shots": n_total,
        "specialist_index": specialist_index,
        "pooled_index": pooled_index,
        "specialist_errors": cand_errors,
        "pooled_errors": base_errors,
        "specialist_ler": cand_errors / n_total,
        "pooled_ler": base_errors / n_total,
        "difference_ler": mean_diff,
        "relative_reduction": (base_errors - cand_errors) / base_errors if base_errors else 0.0,
        "specialist_only_wrong": cand_only,
        "pooled_only_wrong": base_only,
        "prediction_disagreements": pred_disagree,
        "prediction_disagreement_rate": pred_disagree / n_total,
        "root_differences_ler": arr.tolist(),
        "roots_favoring_specialist": int(np.count_nonzero(arr < 0)),
        "roots_favoring_pooled": int(np.count_nonzero(arr > 0)),
        "root_ties": int(np.count_nonzero(arr == 0)),
        "root_bootstrap_ci95": np.quantile(boot, [0.025, 0.975]).tolist(),
        "bootstrap_resamples": draws,
        "bootstrap_seed": seed,
    }


def scan_historical_seeds(outputs_dir: Path, exclude_dir: Path | None = None) -> dict[str, Any]:
    """Conservative read-only scan of recoverable seed/root fields and filenames."""
    found: set[int] = set()
    evidence: list[dict[str, Any]] = []

    def add(value: Any, source: str):
        if isinstance(value, bool):
            return
        if isinstance(value, int) and 0 < value < 2**32:
            found.add(value)
            evidence.append({"seed": value, "source": source})
        elif isinstance(value, list):
            for item in value:
                add(item, source)
        elif isinstance(value, dict):
            if {"start", "step", "count"}.issubset(value):
                start, step, count = value["start"], value["step"], value["count"]
                if all(isinstance(x, int) for x in (start, step, count)):
                    for i in range(max(0, min(count, 100000))):
                        add(start + i * step, source + ":expanded-sequence")
            for k, v in value.items():
                if "seed" in k.lower() or "root" in k.lower():
                    add(v, source + ":" + k)
                elif isinstance(v, (dict, list)):
                    add(v, source)

    for path in outputs_dir.rglob("*"):
        if not path.is_file():
            continue
        if exclude_dir is not None:
            try:
                path.resolve().relative_to(exclude_dir.resolve())
                continue
            except ValueError:
                pass
        rel = str(path.relative_to(outputs_dir))
        for token in re.findall(r"(?<!\d)(\d{8,10})(?!\d)", path.name):
            value = int(token)
            found.add(value)
            evidence.append({"seed": value, "source": rel + ":filename"})
        if path.suffix.lower() == ".json":
            try:
                add(json.loads(path.read_text(encoding="utf-8-sig")), rel)
            except (OSError, ValueError, UnicodeError):
                pass
        elif path.suffix.lower() in (".csv", ".md", ".txt", ".py"):
            try:
                content = path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError):
                continue
            # Capture explicit seed assignments/formulas without treating arbitrary
            # eight-digit data values or hash fragments as seeds.
            for m in re.finditer(
                r"(?i)(?:seed(?:_root|_start|_base|_offset|s)?|root(?:_start|_id)?)"
                r"[^0-9\r\n]{0,48}(\d{7,10})", content
            ):
                value = int(m.group(1))
                found.add(value)
                evidence.append({"seed": value, "source": rel + ":text"})
    unique_evidence = {(x["seed"], x["source"]) for x in evidence}
    return {
        "files_scanned": sum(1 for p in outputs_dir.rglob("*") if p.is_file()),
        "recoverable_unique_seed_values": sorted(found),
        "evidence": [{"seed": s, "source": f} for s, f in sorted(unique_evidence)],
        "coverage_limit": "Only recorded JSON seed/root fields, explicit textual seed assignments, and numeric seed-like filename components are recovered. Unrecorded random streams cannot be ruled out.",
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()
