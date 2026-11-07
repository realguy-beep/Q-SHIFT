"""Q-SHIFT research prototype: a detector-pattern decoder and paired audit.

This is a reproducible software simulation prototype, not hardware integration.
The decoder receives detector bits only. Noise settings select separate training
models in the known-regime experiment; they are never an input feature.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pymatching
import stim


LEVELS = (0.001, 0.003, 0.006)


def take(circuit, n, seed):
    d, o = circuit.compile_detector_sampler(seed=seed).sample(shots=n, separate_observables=True)
    keys = np.packbits(d.astype(np.uint8), axis=1, bitorder="little")[:, 0].astype(np.uint8)
    return keys, d.astype(np.uint8), o[:, 0].astype(np.uint8)


def wilson(k, n):
    z = 1.959963984540054
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [float(center - half), float(center + half)]


def paired_ci(ml_only, match_only, n):
    # Wald interval for paired risk difference; McNemar discordant counts included.
    delta = (ml_only - match_only) / n
    se = np.sqrt(max(0.0, ml_only + match_only - (ml_only - match_only) ** 2 / n)) / n
    return [float(delta - 1.96 * se), float(delta + 1.96 * se)]


def fit_lookup(x, y, alpha=1.0):
    n = np.bincount(x, minlength=256).astype(float)
    e = np.bincount(x, weights=y, minlength=256)
    # Beta(alpha, alpha) smoothing avoids brittle zero-count pattern decisions.
    return (e + alpha) / (n + 2 * alpha)


def choose_threshold(scores, labels):
    candidates = np.r_[-np.inf, np.unique(scores), np.inf]
    return min(((float(np.mean(labels ^ (scores >= t))), float(t)) for t in candidates),
               key=lambda pair: (pair[0], pair[1]))


def run(args):
    results = {
        "title": "Q-SHIFT pattern decoder prototype",
        "status": "simulation-only; no hardware integration",
        "seed": args.seed,
        "protocol": "independent train/validation/test batches, exact 8-bit pattern statistics, threshold fixed on validation, shared test shots across lookup and PyMatching",
        "shots_per_noise": {"train": args.train, "validation": args.validation, "test": args.test},
        "levels": {},
    }
    for i, noise in enumerate(LEVELS):
        c = stim.Circuit.generated("repetition_code:memory", distance=3, rounds=3,
                                   after_clifford_depolarization=noise)
        tx, _, ty = take(c, args.train, args.seed + 100 * i)
        vx, _, vy = take(c, args.validation, args.seed + 100 * i + 1)
        qx, qd, qy = take(c, args.test, args.seed + 100 * i + 2)
        probs = fit_lookup(tx, ty, alpha=args.alpha)
        val_error, threshold = choose_threshold(probs[vx], vy)
        lookup = (probs[qx] >= threshold).astype(np.uint8)
        matching = pymatching.Matching.from_detector_error_model(c.detector_error_model(decompose_errors=True))
        match = np.asarray(matching.decode_batch(qd), dtype=np.uint8).reshape(-1)
        r_lookup, r_match = qy ^ lookup, qy ^ match
        lookup_errors, match_errors = int(r_lookup.sum()), int(r_match.sum())
        ml_only = int(np.sum((r_lookup != 0) & (r_match == 0)))
        matching_only = int(np.sum((r_lookup == 0) & (r_match != 0)))
        results["levels"][str(noise)] = {
            "detectors": c.num_detectors,
            "observable": "L0 parity flip",
            "training_unique_patterns": int(np.unique(tx).size),
            "validation_residual_rate": val_error,
            "threshold": threshold,
            "raw_test": {"errors": int(qy.sum()), "rate": float(qy.mean())},
            "pattern_decoder": {"errors": lookup_errors, "rate": float(r_lookup.mean()),
                                "wilson_95": wilson(lookup_errors, args.test)},
            "pymatching": {"errors": match_errors, "rate": float(r_match.mean()),
                           "wilson_95": wilson(match_errors, args.test)},
            "paired_pattern_minus_matching": {
                "pattern_only_wrong": ml_only,
                "matching_only_wrong": matching_only,
                "net_error_difference": lookup_errors - match_errors,
                "risk_difference_ci_95_approx": paired_ci(ml_only, matching_only, args.test),
            },
        }
        print(noise, json.dumps(results["levels"][str(noise)], indent=2), flush=True)
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train", type=int, default=2_000_000)
    p.add_argument("--validation", type=int, default=200_000)
    p.add_argument("--test", type=int, default=1_000_000)
    p.add_argument("--seed", type=int, default=20261106)
    p.add_argument("--alpha", type=float, default=1.0, help="symmetric Beta prior for each detector pattern")
    p.add_argument("--output", type=Path, default=Path(__file__).with_name("qshift_prototype_results.json"))
    a = p.parse_args()
    if min(a.train, a.validation, a.test) <= 0 or a.alpha <= 0:
        p.error("shot counts and --alpha must be positive")
    results = run(a)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {a.output}")


if __name__ == "__main__":
    main()
