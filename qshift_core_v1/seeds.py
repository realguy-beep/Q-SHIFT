"""Optional, domain-separated seed helpers for future versioned components.

Historical protocols continue using their frozen allocation rules. These
helpers are not imported by existing runners and do not alter any allocation.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

MAX_STIM_SEED = 2_147_483_647


def derive_seed(root_seed: int, namespace: str, index: int = 0) -> int:
    if isinstance(root_seed, bool) or not isinstance(root_seed, int) or not 1 <= root_seed <= MAX_STIM_SEED:
        raise ValueError(f"root_seed must be an integer in [1, {MAX_STIM_SEED}].")
    if not isinstance(namespace, str) or not namespace.strip():
        raise ValueError("namespace must be a nonempty string.")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ValueError("index must be a nonnegative integer.")
    message = f"qshift-core-v1\0{root_seed}\0{namespace}\0{index}".encode("utf-8")
    # The modulus is required by Stim's supported seed range. A ledger below
    # detects the extremely unlikely 31-bit collision before execution.
    value = int.from_bytes(hashlib.sha256(message).digest()[:8], "big")
    return 1 + value % MAX_STIM_SEED


@dataclass
class SeedLedger:
    """Detect derived-seed reuse before any caller allocates a stream."""

    _owners: dict[int, str] = field(default_factory=dict)

    def add(self, seed: int, owner: str) -> int:
        if isinstance(seed, bool) or not isinstance(seed, int) or not 1 <= seed <= MAX_STIM_SEED:
            raise ValueError("seed is outside Stim's supported integer range.")
        if not owner or seed in self._owners:
            prior = self._owners.get(seed)
            raise ValueError(f"seed collision or empty owner: {owner!r} conflicts with {prior!r}.")
        self._owners[seed] = owner
        return seed

    def derive(self, root_seed: int, namespace: str, index: int = 0) -> int:
        seed = derive_seed(root_seed, namespace, index)
        return self.add(seed, f"{namespace}[{index}]")

    def inventory(self) -> dict[str, int]:
        return {owner: seed for seed, owner in sorted(self._owners.items())}
