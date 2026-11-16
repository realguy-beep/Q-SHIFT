"""V1.4 Phase B headroom gate (exploratory development data; matching only).

For each cell (distance x base p x burst family) it samples labeled development
shots at q in {0, 0.01, 0.02} and measures:
  floor       = best static matcher's LER on burst-free (q=0) data, which exactly
                equals a burst oracle's LER at any q (known logically-trivial burst
                signatures XOR out, leaving the q=0 problem);
  static_best = best static matcher over {correlations ON, OFF} x q grid,
                equal-weight LER over q in {0.01, 0.02} (chosen in-sample, which
                biases the baseline low and the ceiling down: conservative);
  ceiling     = 1 - floor / static_best, with a conservative lower bound from
                Clopper-Pearson 97.5% upper (floor) and 2.5% lower (static_best).
A cell qualifies if ceiling_lower >= 0.97 and static_best has >= 100 nonzero errors.
Also times the cost-consistent five-factor decoder on 200 rows (cost only).

Default is a sampler-free dry run. `--prepare-seeds` writes GATE_SEEDS.json once.
`--execute` (owner-authorized only) samples, then writes HEADROOM_GATE.json once.
No raw arrays are saved; these shots are never reused as evaluation data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402

SEEDS_PATH = ROOT / "GATE_SEEDS.json"
OUT_PATH = ROOT / "HEADROOM_GATE.json"
NAMESPACE = "qshift-v1-4-headroom-gate-2026-11-16"
DISTANCES = (3, 5, 7)
BASE_PS = (0.001, 0.002, 0.003)
QS = (0.0, 0.01, 0.02)
SHOTS_PER_Q = 20000
DECODER_Q_GRID = [round(0.0025 * k, 4) for k in range(9)]
CEILING_REQUIRED = 0.97
MIN_STATIC_ERRORS = 100
TIMING_ROWS = 200
SCREENED = (
    "outputs/qshift_correlated_decoder_feasibility_v1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_2/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_3/seed_inventory.json",
    "outputs/qshift_performance_sprint_v1/seed_inventory.json",
)


def cells() -> list[dict]:
    return [{"distance": d, "base_p": p, "family": f}
            for d in DISTANCES for p in BASE_PS for f in m.BURST_FAMILIES]


def seed_label(cell: dict, q: float) -> str:
    return f"gate:d{cell['distance']}:p{cell['base_p']:.3f}:{cell['family']}:q{q:.2f}"


def prepare_seeds() -> dict:
    screened: set[int] = set()
    record = {}
    for rel in SCREENED:
        raw = (REPO / rel).read_bytes()
        vals = set(json.loads(raw)["seeds"].values())
        screened |= vals
        record[rel] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(vals)}
    used, seeds, collisions = set(screened), {}, 0
    for cell in cells():
        for q in QS:
            label, counter = seed_label(cell, q), 0
            while True:
                v = int.from_bytes(hashlib.sha256(f"{NAMESPACE}:{label}:{counter}".encode()).digest()[:8], "big") % (2**31 - 1) + 1
                if v not in used:
                    break
                counter += 1
                collisions += 1
            seeds[label] = v
            used.add(v)
    if set(seeds.values()) & screened or len(set(seeds.values())) != len(seeds):
        raise RuntimeError("gate seed collision")
    return {"schema": "qshift-v1.4-gate-seeds-v1", "namespace": NAMESPACE, "seeds": seeds,
            "screened": record, "union_screened": len(screened), "rejected_collisions": collisions,
            "purpose": "Phase B headroom-gate development shots only; never evaluation data"}


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    from scipy.stats import beta
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def summarize(errors: dict, shots: int) -> dict:
    """errors[(correlations, q_dec)] = [err_q0, err_q001, err_q002]."""
    floor_key = min(errors, key=lambda k: (errors[k][0], k[1], not k[0]))
    static_key = min(errors, key=lambda k: (errors[k][1] + errors[k][2], k[1], not k[0]))
    floor_k = errors[floor_key][0]
    static_k = errors[static_key][1] + errors[static_key][2]
    floor_rate, static_rate = floor_k / shots, static_k / (2 * shots)
    floor_hi = clopper_pearson(floor_k, shots)[1]
    static_lo = clopper_pearson(static_k, 2 * shots)[0]
    ceiling = None if static_rate == 0 else 1 - floor_rate / static_rate
    ceiling_lower = None if static_lo == 0 else 1 - floor_hi / static_lo
    return {"floor_decoder": {"correlations": floor_key[0], "q": floor_key[1]}, "floor_errors": floor_k,
            "floor_ler": floor_rate, "floor_ler_upper_975": floor_hi,
            "static_best_decoder": {"correlations": static_key[0], "q": static_key[1]},
            "static_best_nonzero_errors": static_k, "static_best_nonzero_ler": static_rate,
            "static_best_ler_lower_025": static_lo, "ceiling": ceiling, "ceiling_lower": ceiling_lower,
            "qualifies": bool(ceiling_lower is not None and ceiling_lower >= CEILING_REQUIRED
                              and static_k >= MIN_STATIC_ERRORS)}


def run_cell(cell: dict, seeds: dict) -> dict:
    spec = m.CodeSpec(distance=cell["distance"], gate_p=cell["base_p"], measurement_p=cell["base_p"])
    qubits = m.burst_qubits(spec, cell["family"])
    started = time.perf_counter()
    samples = {}
    for q in QS:
        circuit = m.build_candidate_circuit(spec, q, qubits)
        det, obs = circuit.compile_detector_sampler(seed=seeds[seed_label(cell, q)]).sample(
            shots=SHOTS_PER_Q, separate_observables=True)
        samples[q] = (np.asarray(det, dtype=np.uint8), np.asarray(obs, dtype=np.uint8)[:, 0])
    errors = {}
    for q_dec in DECODER_Q_GRID:
        matching = m.build_matching(m.build_decomposed_dem(m.build_candidate_circuit(spec, q_dec, qubits)))
        for corr in (True, False):
            errors[(corr, q_dec)] = [int(np.count_nonzero(
                np.asarray(matching.decode_batch(samples[q][0], enable_correlations=corr)).reshape(-1) != samples[q][1]))
                for q in QS]
    matching_seconds = time.perf_counter() - started
    events = m.extract_burst_events(spec, qubits)
    base = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(spec)))
    t = time.perf_counter()
    m.FiveFactorDecoder(base, events, spec.detectors, correlations=False).decode_rows(
        samples[0.02][0][:TIMING_ROWS], {"Boff": 0.02})
    five_per_shot = (time.perf_counter() - t) / TIMING_ROWS
    return {**cell, "burst_qubits": list(qubits), "detectors": spec.detectors,
            "shots_per_q": SHOTS_PER_Q, **summarize(errors, SHOTS_PER_Q),
            "errors_by_static_decoder": [{"correlations": c, "q": q, "errors_q0_q001_q002": v}
                                         for (c, q), v in sorted(errors.items())],
            "sampling_and_matching_seconds": matching_seconds,
            "five_factor_seconds_per_shot_timing_only": five_per_shot}


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-seeds", action="store_true")
    mode.add_argument("--execute", action="store_true", help="owner-authorized sampling only")
    args = parser.parse_args()
    if args.prepare_seeds:
        if SEEDS_PATH.exists():
            raise SystemExit("GATE_SEEDS.json exists; seeds are prepared once")
        SEEDS_PATH.write_text(json.dumps(prepare_seeds(), indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print("wrote", SEEDS_PATH.name)
        return
    plan = {"cells": len(cells()), "shots_total": len(cells()) * len(QS) * SHOTS_PER_Q,
            "decoder_grid": DECODER_Q_GRID, "ceiling_required": CEILING_REQUIRED}
    if not args.execute:
        print(json.dumps({"mode": "dry-run", "sampler_calls": 0, **plan}, indent=2))
        return
    if OUT_PATH.exists():
        raise SystemExit("HEADROOM_GATE.json exists; the gate runs once")
    seeds = json.loads(SEEDS_PATH.read_text(encoding="utf-8"))["seeds"]
    results = []
    for cell in cells():
        results.append(run_cell(cell, seeds))
        r = results[-1]
        print(f"d={r['distance']} p={r['base_p']} {r['family']}: floor={r['floor_ler']:.2e} "
              f"static={r['static_best_nonzero_ler']:.2e} ceiling={r['ceiling']} lower={r['ceiling_lower']} "
              f"qualifies={r['qualifies']}", flush=True)
    import pymatching
    import stim
    out = {"schema": "qshift-v1.4-headroom-gate-v1", **plan, "results": results,
           "seeds_sha256": hashlib.sha256(SEEDS_PATH.read_bytes()).hexdigest(),
           "environment": {"python": sys.version.split()[0], "stim": stim.__version__,
                           "pymatching": pymatching.__version__, "numpy": np.__version__},
           "label": "EXPLORATORY development headroom gate; not evidence of decoder performance"}
    OUT_PATH.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
