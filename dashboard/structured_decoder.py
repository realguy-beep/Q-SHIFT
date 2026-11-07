"""Geometry- and round-aware neural decoder for the 40-detector Q-SHIFT pilot.

The encoder uses Stim detector coordinates [x, y, measurement_round] to build
a sparse 3-D grid. A second channel marks occupied detector locations so that
an absent grid cell is distinguishable from a zero-valued syndrome bit.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import torch
from torch import nn


class DetectorGridEncoder(nn.Module):
    """Map [batch, detector] arrays onto a [batch, 2, time, y, x] tensor."""

    def __init__(self, detector_coordinates: Mapping[int, Sequence[float]]):
        super().__init__()
        if not detector_coordinates:
            raise ValueError("Detector coordinates must not be empty.")
        ids = sorted(int(key) for key in detector_coordinates)
        if ids != list(range(len(ids))):
            raise ValueError("Detector IDs must be contiguous from zero.")
        parsed = []
        for detector_id in ids:
            coordinate = detector_coordinates[detector_id]
            if len(coordinate) < 3:
                raise ValueError(f"Detector {detector_id} needs x, y, and round coordinates.")
            x, y, time_index = (float(coordinate[0]), float(coordinate[1]), float(coordinate[2]))
            if not all(torch.isfinite(torch.tensor(v)).item() for v in (x, y, time_index)):
                raise ValueError(f"Detector {detector_id} has a non-finite coordinate.")
            parsed.append((detector_id, x, y, time_index))

        xs = sorted({item[1] for item in parsed})
        ys = sorted({item[2] for item in parsed})
        times = sorted({item[3] for item in parsed})
        x_index = {value: i for i, value in enumerate(xs)}
        y_index = {value: i for i, value in enumerate(ys)}
        t_index = {value: i for i, value in enumerate(times)}
        positions = [(t_index[t], y_index[y], x_index[x]) for _, x, y, t in parsed]
        if len(set(positions)) != len(positions):
            raise ValueError("Multiple detector IDs map to the same (round, y, x) position.")

        self.detector_count = len(ids)
        self.grid_shape = (len(times), len(ys), len(xs))
        self.register_buffer("time_indices", torch.tensor([p[0] for p in positions], dtype=torch.long))
        self.register_buffer("y_indices", torch.tensor([p[1] for p in positions], dtype=torch.long))
        self.register_buffer("x_indices", torch.tensor([p[2] for p in positions], dtype=torch.long))
        occupancy = torch.zeros((1, 1, *self.grid_shape), dtype=torch.float32)
        occupancy[0, 0, self.time_indices, self.y_indices, self.x_indices] = 1.0
        self.register_buffer("occupancy", occupancy)

    def forward(self, detectors: torch.Tensor) -> torch.Tensor:
        if detectors.ndim != 2 or detectors.shape[1] != self.detector_count:
            raise ValueError(f"Expected [batch, {self.detector_count}] detector input.")
        batch = detectors.shape[0]
        time_count, height, width = self.grid_shape
        values = detectors.new_zeros((batch, 1, time_count, height, width), dtype=torch.float32)
        values[:, 0, self.time_indices, self.y_indices, self.x_indices] = detectors.float()
        occupied = self.occupancy.to(device=detectors.device).expand(batch, -1, -1, -1, -1)
        return torch.cat((values, occupied), dim=1)


class StructuredConv3DDecoder(nn.Module):
    """A compact CNN that preserves detector adjacency and round order."""

    def __init__(self, detector_coordinates: Mapping[int, Sequence[float]], channels: int = 16,
                 dropout: float = 0.05):
        super().__init__()
        if channels < 4:
            raise ValueError("channels must be at least four.")
        if not 0.0 <= dropout < 1.0:
            raise ValueError("dropout must be in [0, 1).")
        self.geometry = DetectorGridEncoder(detector_coordinates)
        self.net = nn.Sequential(
            nn.Conv3d(2, channels, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Conv3d(channels, channels * 2, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Dropout3d(dropout),
            nn.AdaptiveAvgPool3d(1),
            nn.Flatten(),
            nn.Linear(channels * 2, 1),
        )

    def forward(self, detectors: torch.Tensor) -> torch.Tensor:
        return self.net(self.geometry(detectors)).squeeze(-1)


class PositionPreservingConv3DDecoder(nn.Module):
    """CNN that retains absolute detector location through a compact flat head.

    Unlike :class:`StructuredConv3DDecoder`, this model does not globally pool
    over space/time. Its parameter count is controlled by ``channels`` and
    ``head_width`` and can be kept close to the MLP baseline.
    """

    def __init__(self, detector_coordinates: Mapping[int, Sequence[float]], channels: int = 4,
                 head_width: int = 16, dropout: float = 0.05):
        super().__init__()
        if channels < 2 or head_width < 2:
            raise ValueError("channels and head_width must be at least two.")
        if not 0.0 <= dropout < 1.0:
            raise ValueError("dropout must be in [0, 1).")
        self.geometry = DetectorGridEncoder(detector_coordinates)
        self.features = nn.Sequential(
            nn.Conv3d(2, channels, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Conv3d(channels, channels * 2, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Dropout3d(dropout),
            nn.Flatten(),
        )
        feature_count = channels * 2
        for size in self.geometry.grid_shape:
            feature_count *= size
        self.head = nn.Sequential(
            nn.Linear(feature_count, head_width),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(head_width, 1),
        )

    def forward(self, detectors: torch.Tensor) -> torch.Tensor:
        return self.head(self.features(self.geometry(detectors))).squeeze(-1)


class DetectorCoordinateGridEncoder(nn.Module):
    """Encode syndrome, occupancy, and normalized physical detector coordinates.

    Coordinate channels are populated only at actual Stim detector locations;
    absent cells remain zero and are distinguished by the occupancy mask.
    Channel order is syndrome, occupancy, time, y, x.
    """

    def __init__(self, detector_coordinates: Mapping[int, Sequence[float]]):
        super().__init__()
        self.base = DetectorGridEncoder(detector_coordinates)
        parsed = [detector_coordinates[i] for i in range(self.base.detector_count)]
        # The source mapping is x, y, measurement-round. Convert each axis to
        # [-1, 1] using its observed range; constant axes map to zero.
        normalized = []
        for axis in (2, 1, 0):  # tensor channel order: time, y, x
            values = torch.tensor([float(row[axis]) for row in parsed], dtype=torch.float32)
            lo, hi = values.min(), values.max()
            if float(hi - lo) == 0.0:
                values = torch.zeros_like(values)
            else:
                values = 2.0 * (values - lo) / (hi - lo) - 1.0
            normalized.append(values)
        time_count, height, width = self.base.grid_shape
        coordinates = torch.zeros((1, 3, time_count, height, width), dtype=torch.float32)
        coordinates[0, :, self.base.time_indices, self.base.y_indices, self.base.x_indices] = torch.stack(normalized)
        self.register_buffer("coordinate_channels", coordinates)

    @property
    def detector_count(self) -> int:
        return self.base.detector_count

    @property
    def grid_shape(self) -> tuple[int, int, int]:
        return self.base.grid_shape

    @property
    def occupancy(self) -> torch.Tensor:
        return self.base.occupancy

    def forward(self, detectors: torch.Tensor) -> torch.Tensor:
        encoded = self.base(detectors)
        coords = self.coordinate_channels.to(device=detectors.device).expand(detectors.shape[0], -1, -1, -1, -1)
        return torch.cat((encoded, coords), dim=1)


class CoordinateChannelConv3DDecoder(nn.Module):
    """Position-aware CNN with explicit normalized detector coordinate maps."""

    def __init__(self, detector_coordinates: Mapping[int, Sequence[float]], channels: int = 4,
                 head_width: int = 16, dropout: float = 0.05):
        super().__init__()
        if channels < 2 or head_width < 2:
            raise ValueError("channels and head_width must be at least two.")
        if not 0.0 <= dropout < 1.0:
            raise ValueError("dropout must be in [0, 1).")
        self.geometry = DetectorCoordinateGridEncoder(detector_coordinates)
        self.features = nn.Sequential(
            nn.Conv3d(5, channels, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Conv3d(channels, channels * 2, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Dropout3d(dropout),
            nn.Flatten(),
        )
        feature_count = channels * 2
        for size in self.geometry.grid_shape:
            feature_count *= size
        self.head = nn.Sequential(
            nn.Linear(feature_count, head_width),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(head_width, 1),
        )

    def forward(self, detectors: torch.Tensor) -> torch.Tensor:
        return self.head(self.features(self.geometry(detectors))).squeeze(-1)


def residual_training_target(matching_prediction: torch.Tensor,
                             observable_flip: torch.Tensor) -> torch.Tensor:
    """Target the parity correction needed on top of matching's prediction."""
    if matching_prediction.shape != observable_flip.shape:
        raise ValueError("Matching predictions and observable labels must have equal shapes.")
    matching_bits = matching_prediction.to(dtype=torch.uint8)
    observable_bits = observable_flip.to(dtype=torch.uint8)
    if torch.any((matching_bits > 1) | (observable_bits > 1)):
        raise ValueError("Matching predictions and observable labels must be binary.")
    return torch.bitwise_xor(matching_bits, observable_bits).to(dtype=torch.float32)


def apply_residual_correction(matching_prediction: torch.Tensor,
                              residual_prediction: torch.Tensor) -> torch.Tensor:
    """Apply a predicted parity correction by XOR with the fixed decoder bit."""
    if matching_prediction.shape != residual_prediction.shape:
        raise ValueError("Matching and residual predictions must have equal shapes.")
    matching_bits = matching_prediction.to(dtype=torch.uint8)
    residual_bits = residual_prediction.to(dtype=torch.uint8)
    if torch.any((matching_bits > 1) | (residual_bits > 1)):
        raise ValueError("Matching and residual predictions must be binary.")
    return torch.bitwise_xor(matching_bits, residual_bits)
