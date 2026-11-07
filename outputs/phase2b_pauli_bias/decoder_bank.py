"""Build the three composition-specific Stim DEM / PyMatching models."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pymatching
import numpy as np

from noise_model import REGIMES, circuit_noise_record


def _canonical_edges(matching: pymatching.Matching):
    result = []
    for u, v, attrs in matching.edges():
        u0 = -1 if u is None else int(u)
        v0 = -1 if v is None else int(v)
        result.append({"u": u0, "v": v0, "weight": float(attrs["weight"]),
                       "fault_ids": sorted(int(x) for x in attrs.get("fault_ids", set()))})
    return result


def _graph_record(matching: pymatching.Matching, dem_text: str, noise: dict, index: int):
    edges = _canonical_edges(matching)
    topology = sorted((min(e["u"], e["v"]), max(e["u"], e["v"])) for e in edges)
    weighted = sorted((e["u"], e["v"], round(e["weight"], 12), tuple(e["fault_ids"])) for e in edges)
    return {
        "decoder_index": index, "assumed_regime": noise["regime"],
        "assumed_gate_fault_probability": noise["total_fault_probability_per_1q_instruction"],
        "assumed_measurement_flip_probability": noise["measurement_flip_probability"],
        "dem_sha256": hashlib.sha256(dem_text.encode("utf-8")).hexdigest(),
        "graph_topology_sha256": hashlib.sha256(repr(topology).encode("utf-8")).hexdigest(),
        "weighted_fault_graph_sha256": hashlib.sha256(repr(weighted).encode("utf-8")).hexdigest(),
        "detectors": matching.num_detectors, "nodes": matching.num_nodes,
        "edges": matching.num_edges,
        "edges_with_logical_fault_ids": sum(bool(e["fault_ids"]) for e in edges),
        "logical_fault_ids": sorted({fid for e in edges for fid in e["fault_ids"]}),
        "edges_detail": edges,
    }


def build_bank(memory_basis: str, *, distance: int = 3, rounds: int = 5,
               gate_p: float = 0.003, measurement_p: float = 0.003,
               bias_ratio: float = 10.0, dem_dir: Path | None = None):
    models = []
    records = []
    for index, regime in enumerate(REGIMES):
        circuit, noise = circuit_noise_record(memory_basis, regime, distance=distance, rounds=rounds,
                                               gate_p=gate_p, measurement_p=measurement_p,
                                               bias_ratio=bias_ratio)
        dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
        if dem.num_detectors != 40 or dem.num_observables != 1:
            raise RuntimeError(f"DEM shape changed for {memory_basis}/{regime}")
        dem_text = str(dem)
        circuit_text = str(circuit)
        matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
        if matching.num_detectors != 40:
            raise RuntimeError(f"matching graph detector count changed for {memory_basis}/{regime}")
        if dem_dir is not None:
            dem_dir.mkdir(parents=True, exist_ok=True)
            (dem_dir / f"dem_{memory_basis}_{regime}.dem").write_text(dem_text, encoding="utf-8")
            (dem_dir / f"circuit_{memory_basis}_{regime}.stim").write_text(circuit_text, encoding="utf-8")
        record = _graph_record(matching, dem_text, noise, index)
        record["circuit_sha256"] = hashlib.sha256(circuit_text.encode("utf-8")).hexdigest()
        record["noise_model"] = noise
        record["dem_approximation"] = {
            "approximate_disjoint_errors": True,
            "decompose_errors": True,
            "pymatching_correlations_enabled": True,
            "explanation": "Stim DEM construction approximates mutually-exclusive PAULI_CHANNEL_1/2 outcomes as independent error mechanisms; PyMatching correlated matching retains available DEM decomposition correlations but does not undo that channel-to-DEM approximation.",
        }
        models.append(matching)
        records.append(record)
    if [r["assumed_regime"] for r in records] != list(REGIMES):
        raise AssertionError("decoder-bank order changed")
    return models, records


def decode_bank(models, detectors: np.ndarray) -> np.ndarray:
    d = np.asarray(detectors, dtype=np.uint8)
    if d.ndim != 2 or d.shape[1] != 40:
        raise ValueError(f"expected detector samples with shape (shots, 40), got {d.shape}")
    predictions = []
    for model in models:
        result = np.asarray(model.decode_batch(d, enable_correlations=True), dtype=np.uint8)
        if result.shape != (len(d), 1):
            raise RuntimeError(f"unexpected decoder output shape {result.shape}")
        predictions.append(result[:, 0])
    return np.stack(predictions)
