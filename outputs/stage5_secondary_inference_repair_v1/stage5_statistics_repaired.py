"""Frozen n=1210 primary analysis plus finite-envelope calibrated secondary family."""
from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from stage5_secondary_stats import conservative_cutoff, dkw_epsilon, envelope_p
from simulate_secondary import draw_mean_sd

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "DESIGN_CONFIG.json").read_text(encoding="utf-8"))
INV = json.loads((HERE / "STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json").read_text(encoding="utf-8"))
SEEDS = {x["role"]: x["seed"] for x in INV["streams"]}
NONZERO = (0.004, 0.008, 0.012, 0.016)


def _holm_adjust(p_values):
    p = np.asarray(p_values, dtype=np.float64)
    order = np.argsort(p, kind="stable")
    adjusted = np.empty_like(p)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (len(p) - rank) * p[index])
        adjusted[index] = min(1.0, running)
    return adjusted.tolist()


@lru_cache(maxsize=1)
def calibrated_secondary_reference():
    refs = []
    fingerprints = []
    n = int(CFG["n_roots_per_condition"])
    m = int(CFG["calibration_replicates_per_family"])
    eps = dkw_epsilon(m, len(CFG["families"]), float(CFG["total_dkw_failure_probability"]))
    for family in CFG["families"]:
        gen = np.random.Generator(np.random.PCG64(SEEDS[f"calibration:{family['name']}"]))
        mean, sd = draw_mean_sd(gen, family["distribution"], m, n, 1, int(CFG["batch_size"]))
        statistic = np.sqrt(n) * mean[:, 0] / sd[:, 0]
        zero = sd[:, 0] == 0
        statistic[zero] = np.where(mean[zero, 0] < 0, -np.inf, np.inf)
        statistic.sort()
        refs.append(statistic)
        fingerprints.append({"family": family["name"], "n": m,
                             "sha256_sorted_t": hashlib.sha256(statistic.tobytes()).hexdigest()})
    cutoffs = {str(float(a)): conservative_cutoff(refs, eps, float(a)) for a in (0.0125, 0.05)}
    return refs, eps, cutoffs, fingerprints


def _root_summary(values):
    x = np.asarray(values, dtype=np.float64)
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all():
        raise ValueError("root differences must be a finite vector")
    mean = float(np.mean(x))
    sd = float(np.std(x, ddof=1))
    return mean, sd / math.sqrt(len(x)), sd


def analyze(groups, cfg, roots):
    g = {float(p): np.asarray(v, dtype=np.float64) for p, v in groups.items()}
    if sorted(g) != [0.0, *NONZERO] or any(x.shape != (roots,) for x in g.values()):
        raise ValueError("Stage 5 repaired inference requires five frozen conditions and n root differences")
    n_frozen = int(CFG["n_roots_per_condition"])
    if roots != n_frozen:
        raise ValueError("root count differs from frozen n=1210 allocation")
    refs, epsilon, secondary_cutoffs, fingerprints = calibrated_secondary_reference()

    # Primary Endpoint B retains the already validated n=1210 procedure.
    means = []
    variances = []
    condition = {}
    p_raw = []
    cond_cutoff = float(secondary_cutoffs["0.0125"])
    for probability in NONZERO:
        x = g[probability]
        mean, se, sd = _root_summary(x)
        means.append(mean)
        variances.append(sd * sd)
        t0 = mean / se if se > 0 else (-math.inf if mean < 0 else math.inf)
        raw_p = float(envelope_p(refs, epsilon, np.asarray([t0]))[0])
        p_raw.append(raw_p)
        condition[str(probability)] = {
            "root_count": roots,
            "mean_difference": mean,
            "sample_sd": sd,
            "standard_error": se,
            "finite_envelope_p_one_sided_vs_zero": raw_p,
            "holm_adjusted_p": None,
            "simultaneous_upper_95_bound": mean - cond_cutoff * se,
            "status": "finite prespecified location-scale envelope; conditional, not distribution-free"
        }

    secondary_holm = _holm_adjust(p_raw)
    for probability, adjusted in zip(NONZERO, secondary_holm):
        condition[str(probability)]["holm_adjusted_p"] = adjusted

    delta = float(np.mean(means))
    primary_se = float(np.sqrt(sum(variances) / (16.0 * roots)))
    df_denom = sum((v / (16.0 * roots)) ** 2 / (roots - 1) for v in variances)
    primary_df = float((primary_se ** 4) / df_denom) if df_denom else math.inf
    primary = cfg["primary_inference"]
    boundary = float(primary["null_boundary"])
    t_boundary = (delta - boundary) / primary_se if primary_se else (-math.inf if delta < boundary else math.inf)
    primary_upper = delta + float(primary["studentized_cutoff"]) * primary_se
    central = [delta - float(primary["central_lower_cutoff"]) * primary_se,
               delta + float(primary["central_upper_cutoff"]) * primary_se]
    p0_mean, p0_se, _ = _root_summary(g[0.0])
    p0_upper = p0_mean + float(primary["p0_one_sided_cutoff"]) * p0_se
    condition_means = list(means)
    return {
        "estimand": "equal-weight mean of four nonzero-condition root-paired adaptive-minus-fixed LER differences",
        "primary_delta": delta,
        "primary_standard_error": primary_se,
        "primary_df_reference": primary_df,
        "primary_t_statistic_at_boundary": t_boundary,
        "primary_boundary": boundary,
        "primary_calibrated_critical": float(primary["studentized_cutoff"]),
        "primary_one_sided_upper_bound": primary_upper,
        "primary_central_interval_candidate": central,
        "primary_calibrated_reject": bool(primary_upper < boundary),
        "p0_mean_difference": p0_mean,
        "p0_standard_error": p0_se,
        "p0_upper_bound": p0_upper,
        "p0_no_harm_boundary": float(primary["p0_no_harm_boundary"]),
        "p0_no_harm_pass": bool(p0_upper <= float(primary["p0_no_harm_boundary"])),
        "nonzero_condition_means": {str(p): m for p, m in zip(NONZERO, condition_means)},
        "secondary_finite_envelope_p_raw": p_raw,
        "secondary_finite_envelope_p_holm": secondary_holm,
        "secondary_condition_details": condition,
        "secondary_reference": {"dkw_epsilon": epsilon, "dkw_delta_total": float(CFG["total_dkw_failure_probability"]),
                                "fingerprints": fingerprints, "roots_per_condition": roots},
        "overall_candidate_gate": bool(primary_upper < boundary and p0_upper <= float(primary["p0_no_harm_boundary"]) and all(m < 0 for m in condition_means) and max(condition_means) <= 0.0002),
        "inference_scope": "primary Endpoint B uses the frozen n=1210 design cutoffs. Secondary condition-level Holm p-values are calibrated for the six prespecified root-effect location-scale shapes only; claims are not distribution-free.",
        "resampling_unit": "independent root; paired shot errors reduced to one root-level difference before inference"
    }
