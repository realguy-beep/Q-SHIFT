"""Versioned Q-SHIFT decoder and evaluation integration contracts.

This package is infrastructure only. It does not sample circuits, change a
noise model, or make a performance claim about any decoder.
"""

__version__ = "1.0.0"

from .contracts import DecoderMetadata, DecoderPrediction, DecoderProtocol
from .baselines import IdentityObservableDecoder
from .pymatching_adapter import PyMatchingDecoder

__all__ = [
    "DecoderMetadata",
    "DecoderPrediction",
    "DecoderProtocol",
    "IdentityObservableDecoder",
    "PyMatchingDecoder",
    "__version__",
]
