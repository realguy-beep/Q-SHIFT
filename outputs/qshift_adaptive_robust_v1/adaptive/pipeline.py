"""Causal adaptive pipeline prototype (ADAPTIVE_ARCHITECTURE.md).

detectors(block t) -> [decision for block t uses ONLY blocks < t] -> decode block t with the selected decoder
-> update estimators with block t detectors (feedback / recalibration).

Built on the existing `qshift_core_v1.controller` registry and `SafeDecoderSelector`, unchanged: low
confidence, UNKNOWN regimes, missing estimates and non-causal proposals all fall back to the registered fixed
decoder, and switches obey hysteresis and dwell. The pipeline accepts detector rows only; it has no argument
through which observables, true noise parameters or true burst supports could enter.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np

from qshift_core_v1.controller import (DecoderRegistry, NoiseEstimate, SafeDecoderSelector,
                                       SelectionDecision, SelectionProposal)

from .changepoint import BinomialCUSUM
from .estimation import estimate_background_scale
from .regime import UNKNOWN, RegimeClassifier


@dataclass
class BlockRecord:
    block: int
    decision: SelectionDecision
    regime: str
    regime_confidence: float
    change_alarm: bool
    background_scale: float | None
    predictions: np.ndarray


@dataclass
class AdaptiveController:
    registry: DecoderRegistry
    fallback: str
    classifier: RegimeClassifier
    decoder_for_regime: dict[str, str]
    nominal_rates: np.ndarray
    calibration_blocks: int = 3
    window_blocks: int = 4
    cusum_delta: float = 0.2
    cusum_threshold: float = 8.0
    minimum_confidence: float = 0.9
    hysteresis_blocks: int = 2
    minimum_dwell_blocks: int = 2
    history: list[BlockRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        unknown = set(self.decoder_for_regime.values()) - set(self.registry.names())
        if unknown:
            raise ValueError(f"regime map names unregistered decoders: {sorted(unknown)}")
        self.selector = SafeDecoderSelector(self.registry, fallback_name=self.fallback,
                                            minimum_confidence=self.minimum_confidence,
                                            hysteresis_blocks=self.hysteresis_blocks,
                                            minimum_dwell_blocks=self.minimum_dwell_blocks)
        self._window: deque[np.ndarray] = deque(maxlen=self.window_blocks)
        self._calib: list[np.ndarray] = []
        self._cusum: BinomialCUSUM | None = None
        self._proposal: SelectionProposal | None = None
        self._last_regime, self._last_conf, self._last_scale = UNKNOWN, 0.0, None

    def step(self, block: int, detectors: np.ndarray) -> BlockRecord:
        det = np.asarray(detectors, dtype=np.uint8)
        # 1. decide for this block from earlier blocks only
        decision = self.selector.choose(block, self._proposal)
        pred = self.registry.get(decision.selected_decoder).decode(det).bits
        # 2. feedback: update estimators with this block's detectors (never with predictions or labels)
        alarm = self._update(block, det)
        rec = BlockRecord(block, decision, self._last_regime, self._last_conf, alarm, self._last_scale, pred)
        self.history.append(rec)
        return rec

    def _update(self, block: int, det: np.ndarray) -> bool:
        trials = det.size
        if self._cusum is None:
            self._calib.append(det)
            if len(self._calib) >= self.calibration_blocks:
                pooled = np.concatenate(self._calib)
                r0 = float(np.clip(pooled.mean(), 1e-6, 0.49))
                self._cusum = BinomialCUSUM(r0, self.cusum_delta, self.cusum_threshold, trials)
            self._proposal = None
            return False
        alarm = self._cusum.update(int(det.sum())) if det.size == self._cusum.trials_per_block else False
        if alarm:
            self._window.clear()             # a change invalidates older evidence
        self._window.append(det)
        rows = np.concatenate(self._window)
        res = self.classifier.classify(rows)
        scale = estimate_background_scale(rows, self.nominal_rates)
        self._last_regime, self._last_conf, self._last_scale = res.label, res.confidence, scale.scale[0]
        if res.label == UNKNOWN or res.label not in self.decoder_for_regime:
            self._proposal = None
        else:
            est = NoiseEstimate(parameters={"background_scale": scale.scale[0]}, confidence=res.confidence,
                                calibration_shots=int(rows.shape[0]))
            self._proposal = SelectionProposal(decoder_name=self.decoder_for_regime[res.label],
                                               confidence=res.confidence, based_on_through_block=block,
                                               reason=f"regime {res.label} (p_fit={res.fit_pvalue:.3g})",
                                               estimate=est)
        return alarm
