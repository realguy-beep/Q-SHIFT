"""Small, position-preserving CNN candidates for residual QEC decoding.

These models predict a *residual parity correction* on top of a supplied
PyMatching observable prediction. They do not apply physical gates. The
module is isolated under outputs/ so historical dashboard and experiment
implementations remain unchanged.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import torch
from torch import nn

from dashboard.structured_decoder import DetectorGridEncoder


class ResidualConv3DBlock(nn.Module):
    """One full 3-D convolution with an identity skip connection."""

    def __init__(self, channels: int, dropout: float = 0.05):
        super().__init__()
        if channels < 2:
            raise ValueError("channels must be at least two")
        if not 0.0 <= dropout < 1.0:
            raise ValueError("dropout must be in [0, 1)")
        self.conv = nn.Conv3d(channels, channels, kernel_size=3, padding=1)
        self.activation = nn.GELU()
        self.dropout = nn.Dropout3d(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        update = self.conv(x)
        update = self.activation(update)
        update = self.dropout(update)
        return self.activation(x + update)


class FactorizedSpatialTemporalBlock(nn.Module):
    """Depthwise spatial/temporal filters with pointwise channel mixing."""

    def __init__(self, channels: int, dropout: float = 0.05):
        super().__init__()
        if channels < 2:
            raise ValueError("channels must be at least two")
        if not 0.0 <= dropout < 1.0:
            raise ValueError("dropout must be in [0, 1)")
        self.spatial_depthwise = nn.Conv3d(
            channels, channels, kernel_size=(1, 3, 3), padding=(0, 1, 1),
            groups=channels, bias=False,
        )
        self.temporal_depthwise = nn.Conv3d(
            channels, channels, kernel_size=(3, 1, 1), padding=(1, 0, 0),
            groups=channels, bias=False,
        )
        self.activation = nn.GELU()
        self.dropout = nn.Dropout3d(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        update = self.spatial_depthwise(x)
        update = self.activation(update)
        update = self.dropout(update)
        update = self.temporal_depthwise(update)
        return self.activation(x + update)


class _ResidualPositionBase(nn.Module):
    """Shared input/output convention and position-preserving dense head."""

    def __init__(self, detector_coordinates: Mapping[int, Sequence[float]],
                 head_width: int, dropout: float):
        super().__init__()
        if head_width < 2:
            raise ValueError("head_width must be at least two")
        if not 0.0 <= dropout < 1.0:
            raise ValueError("dropout must be in [0, 1)")
        self.geometry = DetectorGridEncoder(detector_coordinates)
        self.dropout = nn.Dropout(dropout)
        self.head_width = head_width
        self.dropout_rate = dropout

    def _make_head(self, feature_channels: int) -> nn.Sequential:
        feature_count = feature_channels
        for size in self.geometry.grid_shape:
            feature_count *= size
        # One additional scalar carries the frozen matching prediction.
        return nn.Sequential(
            nn.Linear(feature_count + 1, self.head_width),
            nn.GELU(),
            nn.Dropout(self.dropout_rate),
            nn.Linear(self.head_width, 1),
        )

    @staticmethod
    def _append_matching_bit(features: torch.Tensor,
                             matching_prediction: torch.Tensor) -> torch.Tensor:
        batch = features.shape[0]
        pm = torch.as_tensor(matching_prediction, device=features.device,
                             dtype=features.dtype)
        if pm.ndim == 2 and pm.shape[1] == 1:
            pm = pm[:, 0]
        if pm.ndim != 1 or pm.shape[0] != batch:
            raise ValueError("matching_prediction must have shape [batch] or [batch, 1]")
        # Do not inspect tensor values here: on CUDA that would synchronize the
        # stream on every forward pass. The paired data/decoder boundary
        # validates that matching outputs are binary before model inference.
        return torch.cat((features.flatten(start_dim=1), pm.reshape(batch, 1)), dim=1)


class ResidualPositionCNNV2(_ResidualPositionBase):
    """Full 3-D residual CNN that retains the absolute detector grid.

    A narrow 4-channel feature map and wider compact head keep parameters and
    multiply-add cost near the existing residual-position CNN.
    """

    def __init__(self, detector_coordinates: Mapping[int, Sequence[float]],
                 channels: int = 4, head_width: int = 32, dropout: float = 0.05):
        if channels < 2:
            raise ValueError("channels must be at least two")
        super().__init__(detector_coordinates, head_width, dropout)
        # Keep channel width constant at four: the residual block does not
        # require a projection, and absolute position is retained by flattening.
        self.stem = nn.Sequential(
            nn.Conv3d(2, channels, kernel_size=3, padding=1),
            nn.GELU(),
        )
        self.residual_block = ResidualConv3DBlock(channels, dropout=dropout)
        self.head = self._make_head(channels)

    def forward(self, detectors: torch.Tensor,
                matching_prediction: torch.Tensor) -> torch.Tensor:
        features = self.residual_block(self.stem(self.geometry(detectors)))
        return self.head(self._append_matching_bit(features, matching_prediction)).squeeze(-1)


class FactorizedSpatialTemporalResidualCNN(_ResidualPositionBase):
    """Compact separable CNN with distinct spatial and round-order filters."""

    def __init__(self, detector_coordinates: Mapping[int, Sequence[float]],
                 channels: int = 4, head_width: int = 32, dropout: float = 0.05):
        if channels < 2:
            raise ValueError("channels must be at least two")
        super().__init__(detector_coordinates, head_width, dropout)
        hidden = channels
        self.stem = nn.Sequential(
            nn.Conv3d(2, channels, kernel_size=3, padding=1),
            nn.GELU(),
        )
        self.factorized_block = FactorizedSpatialTemporalBlock(hidden, dropout=dropout)
        self.head = self._make_head(hidden)

    def forward(self, detectors: torch.Tensor,
                matching_prediction: torch.Tensor) -> torch.Tensor:
        features = self.factorized_block(self.stem(self.geometry(detectors)))
        return self.head(self._append_matching_bit(features, matching_prediction)).squeeze(-1)


def build_candidate(name: str, detector_coordinates: Mapping[int, Sequence[float]]) -> nn.Module:
    """Construct one versioned candidate by its stable protocol name."""
    if name == "residual_position_v2":
        return ResidualPositionCNNV2(detector_coordinates)
    if name == "factorized_spatiotemporal_residual":
        return FactorizedSpatialTemporalResidualCNN(detector_coordinates)
    raise ValueError(f"Unknown Stage 1 architecture: {name}")


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())
