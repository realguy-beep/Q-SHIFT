"""Compact direct and residual neural decoders."""
from __future__ import annotations

import torch
from torch import nn


class DirectMLP(nn.Module):
    """Small 40-bit detector-to-logical-flip baseline."""
    def __init__(self, detector_count: int = 40):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(detector_count, 128), nn.GELU(), nn.Dropout(0.05),
            nn.Linear(128, 64), nn.GELU(), nn.Linear(64, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


class ResidualMLP(nn.Module):
    """Predicts a logical parity correction to the frozen matching output."""
    def __init__(self, detector_count: int = 40):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(detector_count + 1, 128), nn.GELU(), nn.Dropout(0.05),
            nn.Linear(128, 64), nn.GELU(), nn.Linear(64, 1),
        )

    def forward(self, detectors, matching_prediction):
        x = torch.cat([detectors, matching_prediction.reshape(-1, 1)], dim=1)
        return self.net(x).squeeze(-1)

