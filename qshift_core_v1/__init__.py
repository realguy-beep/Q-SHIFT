"""Versioned Q-SHIFT decoder and evaluation integration contracts.

This package is infrastructure only. It does not sample circuits, change a
noise model, or make a performance claim about any decoder.
"""

__version__ = "1.0.0"

from .contracts import DecoderMetadata, DecoderPrediction, DecoderProtocol
from .baselines import IdentityObservableDecoder
from .pymatching_adapter import PyMatchingDecoder
from .sampling_model_identity import (
    DEMConstructionRecord,
    DEMConstructionSettingsV2,
    DecoderModelIdentity,
    DetectorBatch,
    IdentityAwareDecoderRegistry,
    SamplingIdentity,
    StimDEMArtifact,
    TrustedDetectorBatchAdapter,
    assert_model_compatible,
    decode_model_checked,
    evaluate_identity_aware_paired,
)

__all__ = [
    "DecoderMetadata",
    "DecoderPrediction",
    "DecoderProtocol",
    "IdentityObservableDecoder",
    "PyMatchingDecoder",
    "SamplingIdentity",
    "DecoderModelIdentity",
    "DEMConstructionSettingsV2",
    "DEMConstructionRecord",
    "StimDEMArtifact",
    "DetectorBatch",
    "TrustedDetectorBatchAdapter",
    "IdentityAwareDecoderRegistry",
    "assert_model_compatible",
    "decode_model_checked",
    "evaluate_identity_aware_paired",
    "__version__",
]
