"""Detector-only background-scale estimation, robust to localized bursts (hypothesis H-E1).

Motivation (qshift_d5_model_mismatch_v1/DIAG_RESULTS.md): the Phase C learner compares observed detector
statistics against a NOMINAL base model. A global base-p error shifts every residual the same way, which
either hides the burst (true p lower) or fakes one (true p higher).

H-E1: a background mis-scale is GLOBAL (it moves every detector class), while a weight-3 burst is LOCAL (it
moves a handful of detectors). A robust location estimate (median / trimmed mean) of log(observed/nominal)
detector rates therefore estimates the background scale without being pulled by the burst, and the
residuals after rescaling isolate the burst.

This module is pure numpy and uses detector rows only. It never sees observables, true p or true supports.
Low-rate approximation: a detector's flip probability is ~linear in the mechanism probabilities when p << 1,
so one multiplicative scale per detector CLASS is identifiable. Per-class scales (e.g. bulk vs boundary,
or space-like vs time-like) are the hook for biased noise (Mz), where classes are scaled differently.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ScaleEstimate:
    scale: dict[int, float]            # class id -> multiplicative background scale
    log_scale_se: dict[int, float]     # approximate standard error of log scale per class
    shots: int
    outlier_detectors: tuple[int, ...]  # detectors whose rescaled residual is a robust outlier


def detector_rates(detectors: np.ndarray) -> np.ndarray:
    d = np.asarray(detectors, dtype=np.uint8)
    if d.ndim != 2 or d.shape[0] == 0:
        raise ValueError("detectors must be a non-empty [shots, detectors] array")
    return d.mean(axis=0)


def _trimmed_mean(x: np.ndarray, trim: float) -> float:
    x = np.sort(np.asarray(x, dtype=float))
    k = int(np.floor(trim * len(x)))
    core = x[k: len(x) - k] if len(x) - 2 * k > 0 else x
    return float(core.mean())


def estimate_background_scale(detectors: np.ndarray, nominal_rates: np.ndarray, classes: np.ndarray | None = None,
                              *, trim: float = 0.2, outlier_z: float = 6.0) -> ScaleEstimate:
    """Robust per-class multiplicative scale of detector rates relative to the nominal model.

    Within each class, scale = exp(trimmed mean of log(observed / nominal)). Detectors with a rescaled
    excess beyond `outlier_z` binomial standard errors are reported as candidate burst detectors.
    """
    rates = detector_rates(detectors)
    nom = np.asarray(nominal_rates, dtype=float)
    if nom.shape != rates.shape or np.any(nom <= 0) or np.any(nom >= 0.5):
        raise ValueError("nominal_rates must match detector count and lie in (0, 0.5)")
    if not 0.0 <= trim < 0.5:
        raise ValueError("trim must be in [0, 0.5)")
    n = int(np.asarray(detectors).shape[0])
    cls = np.zeros(len(nom), dtype=int) if classes is None else np.asarray(classes, dtype=int)
    if cls.shape != nom.shape:
        raise ValueError("classes must match detector count")
    obs = np.maximum(rates, 0.5 / n)                       # avoid log(0); continuity correction
    lr = np.log(obs / nom)
    scale, se = {}, {}
    fitted = np.empty_like(nom)
    for c in np.unique(cls):
        idx = cls == c
        s = _trimmed_mean(lr[idx], trim)
        scale[int(c)] = float(np.exp(s))
        # delta-method SE of a log-rate is ~ 1/sqrt(n * rate); divide by sqrt(#detectors used)
        used = max(1, int(idx.sum() - 2 * np.floor(trim * idx.sum())))
        se[int(c)] = float(np.sqrt(np.mean(1.0 / (n * obs[idx]))) / np.sqrt(used))
        fitted[idx] = np.clip(nom[idx] * np.exp(s), 1e-12, 0.5)
    z = (rates - fitted) / np.sqrt(fitted * (1 - fitted) / n)
    outliers = tuple(int(i) for i in np.flatnonzero(z > outlier_z))
    return ScaleEstimate(scale=scale, log_scale_se=se, shots=n, outlier_detectors=outliers)


def rescaled_nominal(nominal_rates: np.ndarray, est: ScaleEstimate, classes: np.ndarray | None = None) -> np.ndarray:
    nom = np.asarray(nominal_rates, dtype=float)
    cls = np.zeros(len(nom), dtype=int) if classes is None else np.asarray(classes, dtype=int)
    return np.clip(nom * np.array([est.scale[int(c)] for c in cls]), 1e-12, 0.5)


def log_residual(detectors: np.ndarray, reference_rates: np.ndarray) -> np.ndarray:
    """Per-detector residual log(observed/reference), the quantity whose uniform offset broke Phase C."""
    n = np.asarray(detectors).shape[0]
    return np.log(np.maximum(detector_rates(detectors), 0.5 / n) / np.asarray(reference_rates, dtype=float))
