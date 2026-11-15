"""Exact multi-prior evaluation of the frozen V1.1 five-factor decoder.

For one syndrome, the 32 burst-subset residuals, their background PyMatching costs
and logical parities do not depend on q. This module computes them once and then
applies several q priors (B per-root q-hat, Bstatic, C true q). Each choice is
bit-identical to `model.BurstEnumerationDecoder(...).decode_one`, which tests pin.
It reuses computation only; it does not change the decoder.
"""
from __future__ import annotations

import math

import numpy as np

from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (
    BurstEnumerationDecoder,
    BurstEvent,
)


class MultiPriorFiveFactor:
    def __init__(self, background_matching, events: tuple[BurstEvent, ...]):
        # Reuse the frozen class's constructor checks and edge tables.
        self._ref = BurstEnumerationDecoder(background_matching, events, 0.01)
        self.matching = background_matching
        self.events = events

    def _options(self, syndrome: np.ndarray) -> list[tuple[int, int, float, int]]:
        ref = self._ref
        options = []
        for mask in range(1 << len(self.events)):
            residual = np.asarray(syndrome, dtype=np.uint8).copy()
            logical = 0
            burst_count = 0
            for index, event in enumerate(self.events):
                if (mask >> index) & 1:
                    residual[list(event.detector_ids)] ^= 1
                    logical ^= event.observable_flip
                    burst_count += 1
            edges = self.matching.decode_to_edges_array(residual, enable_correlations=True)
            background_cost = 0.0
            background_logical = 0
            for edge in edges:
                key = ((int(edge[0]), -1) if int(edge[1]) == -1
                       else tuple(sorted((int(edge[0]), int(edge[1])))))
                try:
                    background_cost += ref.edge_weights[key]
                    background_logical ^= ref.edge_logical_parity[key]
                except KeyError as exc:
                    raise RuntimeError(f"PyMatching returned an unrecognized edge {exc}") from exc
            options.append((burst_count, mask, float(background_cost), background_logical ^ logical))
        return options

    @staticmethod
    def _choose(options, q: float) -> int:
        log_odds = math.log((1.0 - q) / q)
        return min((cost + count * log_odds, count, mask, prediction)
                   for count, mask, cost, prediction in options)[3]

    def decode_rows(self, detectors: np.ndarray, priors: dict[str, float]) -> dict[str, np.ndarray]:
        """Return {name: uint8 [shots,1]} for each named prior q in [0, 0.02]."""
        x = np.asarray(detectors)
        if x.ndim != 2 or x.shape[1] != 40 or not np.isin(x, [0, 1]).all():
            raise ValueError("detectors must be a binary [shots,40] array")
        for name, q in priors.items():
            if not math.isfinite(q) or not 0.0 <= q <= 0.02:
                raise ValueError(f"invalid prior for {name}: {q}")
        out = {name: np.empty((len(x), 1), dtype=np.uint8) for name in priors}
        zero_names = [name for name, q in priors.items() if q == 0.0]
        positive = {name: q for name, q in priors.items() if q != 0.0}
        if zero_names:
            # Frozen decode_one fast path at q=0: plain correlated PyMatching per row.
            zero = np.asarray([int(np.asarray(self.matching.decode(row, enable_correlations=True)).reshape(-1)[0])
                               for row in x], dtype=np.uint8)
            for name in zero_names:
                out[name][:, 0] = zero
        if positive:
            for row_i, syndrome in enumerate(x):
                options = self._options(syndrome)
                for name, q in positive.items():
                    out[name][row_i, 0] = self._choose(options, q)
        return out
