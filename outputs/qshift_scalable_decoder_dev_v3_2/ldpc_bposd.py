"""V3.2: compiled BP+OSD (ldpc==2.4.1) on V3's hypergraph-preserving DEM matrix.

H, L and p come unchanged from V3 `dem_to_matrix(merge=True)`; each DEM mechanism
(hyperedges and burst mechanisms included) is one column with its logical bit. ldpc
returns a fault estimate e-hat; the prediction is the exact parity L.e-hat (plus the
p=1 logical offset). Frozen settings: see PROTOCOL.md.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from ldpc import BpOsdDecoder

from outputs.qshift_scalable_decoder_dev_v3.bposd import dem_to_matrix

SETTINGS = {"bp_method": "product_sum", "schedule": "parallel", "max_iter": 50,
            "osd_method": "OSD_CS", "osd_order": 10}


def gf2_rank(H: np.ndarray) -> int:
    """Rank of a binary matrix over GF(2) (row reduction)."""
    a = (np.asarray(H) % 2).astype(np.uint8).copy()
    rank = 0
    rows, cols = a.shape
    for c in range(cols):
        pivot = next((r for r in range(rank, rows) if a[r, c]), None)
        if pivot is None:
            continue
        a[[rank, pivot]] = a[[pivot, rank]]
        for r in range(rows):
            if r != rank and a[r, c]:
                a[r] ^= a[rank]
        rank += 1
        if rank == rows:
            break
    return rank


class LdpcBPOSD:
    def __init__(self, dem, settings: dict | None = None):
        self.dm = dem_to_matrix(dem, merge=True)
        cfg = {**SETTINGS, **(settings or {})}
        # ldpc 2.4.1 crashes the process at teardown when osd_order exceeds the number of
        # non-pivot columns (n - rank); observed on tiny toy DEMs only. Clamp; on every real
        # DEM here n - rank is in the hundreds, so the frozen order 10 is used unchanged.
        free = self.dm.H.shape[1] - gf2_rank(self.dm.H)
        self.osd_order_used = min(int(cfg["osd_order"]), max(free, 0))
        cfg["osd_order"] = self.osd_order_used
        self.decoder = BpOsdDecoder(sp.csr_matrix(self.dm.H), error_channel=list(map(float, self.dm.p)), **cfg)
        self.L = self.dm.L.astype(np.int64)

    def fault_estimate(self, syndrome: np.ndarray) -> np.ndarray:
        s = np.asarray(syndrome, dtype=np.uint8) ^ self.dm.offset_detectors
        return np.asarray(self.decoder.decode(s), dtype=np.uint8)

    def decode_one(self, syndrome: np.ndarray) -> int:
        e = self.fault_estimate(syndrome)
        return int((int(e.astype(np.int64) @ self.L) % 2) ^ self.dm.offset_logical)

    def decode_batch(self, x: np.ndarray) -> np.ndarray:
        return np.asarray([self.decode_one(row) for row in np.asarray(x, dtype=np.uint8)], dtype=np.uint8).reshape(-1, 1)
