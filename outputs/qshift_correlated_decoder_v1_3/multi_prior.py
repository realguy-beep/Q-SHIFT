"""Mode-aware exact multi-prior evaluation of the five-factor decoder.

`correlations=True` reproduces the frozen V1.1/V1.2 decoder bit-for-bit, including
its cost mismatch: residual edges are chosen by correlation-reweighted matching
but scored with static edge weights. `correlations=False` is the cost-consistent
repair: edges are chosen by uncorrelated matching, which minimizes exactly the
static-weight sum used as the background cost (pinned by a test against
PyMatching's own `return_weight`). The q=0 fast path uses the same mode.
"""
from __future__ import annotations

import math

import numpy as np

from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (
    BurstEnumerationDecoder,
    BurstEvent,
)


class ModeAwareFiveFactor:
    def __init__(self, background_matching, events: tuple[BurstEvent, ...], *, correlations: bool):
        self._ref = BurstEnumerationDecoder(background_matching, events, 0.01)  # frozen checks + edge tables
        self.matching = background_matching
        self.events = events
        self.correlations = bool(correlations)

    def options(self, syndrome: np.ndarray) -> list[tuple[int, int, float, int]]:
        ref = self._ref
        out = []
        for mask in range(1 << len(self.events)):
            residual = np.asarray(syndrome, dtype=np.uint8).copy()
            logical = 0
            count = 0
            for index, event in enumerate(self.events):
                if (mask >> index) & 1:
                    residual[list(event.detector_ids)] ^= 1
                    logical ^= event.observable_flip
                    count += 1
            edges = self.matching.decode_to_edges_array(residual, enable_correlations=self.correlations)
            cost = 0.0
            parity = 0
            for edge in edges:
                key = ((int(edge[0]), -1) if int(edge[1]) == -1
                       else tuple(sorted((int(edge[0]), int(edge[1])))))
                try:
                    cost += ref.edge_weights[key]
                    parity ^= ref.edge_logical_parity[key]
                except KeyError as exc:
                    raise RuntimeError(f"PyMatching returned an unrecognized edge {exc}") from exc
            out.append((count, mask, float(cost), parity ^ logical))
        return out

    @staticmethod
    def choose(options, q: float) -> int:
        log_odds = math.log((1.0 - q) / q)
        return min((cost + count * log_odds, count, mask, prediction)
                   for count, mask, cost, prediction in options)[3]

    def decode_rows(self, detectors: np.ndarray, priors: dict[str, float]) -> dict[str, np.ndarray]:
        x = np.asarray(detectors)
        if x.ndim != 2 or x.shape[1] != 40 or not np.isin(x, [0, 1]).all():
            raise ValueError("detectors must be a binary [shots,40] array")
        for name, q in priors.items():
            if not math.isfinite(q) or not 0.0 <= q <= 0.02:
                raise ValueError(f"invalid prior for {name}: {q}")
        out = {name: np.empty((len(x), 1), dtype=np.uint8) for name in priors}
        zero = [n for n, q in priors.items() if q == 0.0]
        positive = {n: q for n, q in priors.items() if q != 0.0}
        if zero:
            z = np.asarray([int(np.asarray(self.matching.decode(row, enable_correlations=self.correlations)).reshape(-1)[0])
                            for row in x], dtype=np.uint8)
            for n in zero:
                out[n][:, 0] = z
        if positive:
            for i, row in enumerate(x):
                opts = self.options(row)
                for n, q in positive.items():
                    out[n][i, 0] = self.choose(opts, q)
        return out
