"""CUDA inference-only benchmark on saved detector rows; generates no shots or labels."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

from models import DirectMLP, ResidualMLP


def benchmark(run_dir: Path, repeats: int = 50, warmups: int = 5) -> dict:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available in this PyTorch installation; install a compatible CUDA wheel first.")
    run_dir = run_dir.resolve()
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    checkpoint = torch.load(run_dir / "checkpoint.pt", map_location="cpu", weights_only=False)
    with np.load(run_dir / metadata["test_evidence_path"], allow_pickle=False) as data:
        detectors = np.asarray(data["detectors"], dtype=np.float32)
        fixed = np.asarray(data["pymatching"], dtype=np.uint8)
        expected_direct = np.asarray(data["direct_neural"], dtype=np.uint8)
    device = torch.device("cuda:0")
    direct, residual = DirectMLP().to(device), None
    direct.load_state_dict(checkpoint["direct_state"])
    direct.eval()
    if metadata["config"]["model_selection"] == "direct_plus_residual":
        residual = ResidualMLP().to(device)
        residual.load_state_dict(checkpoint["residual_state"])
        residual.eval()
    x = torch.from_numpy(detectors).to(device)
    b = torch.from_numpy(fixed.astype(np.float32)).to(device)
    with torch.inference_mode():
        got = (torch.sigmoid(direct(x)) >= 0.5).to(torch.uint8).cpu().numpy()
        if not np.array_equal(got, expected_direct):
            raise RuntimeError("CUDA direct predictions differ from saved CPU predictions on the same detectors.")
        if residual is not None:
            residual(x, b)
        torch.cuda.synchronize(device)
        timings = {}
        for name, fn in (("direct_mlp", lambda: direct(x)),
                         ("residual_mlp", lambda: residual(x, b)) if residual is not None else ("residual_mlp", None)):
            if fn is None:
                continue
            for _ in range(warmups):
                fn()
            torch.cuda.synchronize(device)
            torch.cuda.reset_peak_memory_stats(device)
            tick = time.perf_counter()
            for _ in range(repeats):
                fn()
            torch.cuda.synchronize(device)
            elapsed = time.perf_counter() - tick
            timings[name] = {"shots_per_pass": int(len(detectors)), "repeats": int(repeats),
                             "total_seconds": elapsed,
                             "mean_seconds_per_pass": elapsed / repeats,
                             "shots_per_second": len(detectors) * repeats / elapsed}
    return {"status": "PASS", "run_id": metadata["run_id"], "device": torch.cuda.get_device_name(0),
            "torch_version": torch.__version__, "benchmark_scope": "inference only; saved test detector features, no labels read, no samples generated",
            "prediction_recheck": "CUDA direct outputs exactly match the saved CPU direct predictions",
            "timings": timings, "peak_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
            "peak_reserved_bytes": int(torch.cuda.max_memory_reserved(device))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--repeats", type=int, default=50)
    parser.add_argument("--warmups", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.run_dir, args.repeats, args.warmups), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
