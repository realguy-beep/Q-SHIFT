"""One seed-use specification for runner and analyser (audit F4).

DB8's runner and analyser each had their own idea of which seeds an episode uses, and they disagreed on blocks 0-5.
Here both read SeedSpec: the runner can only draw a seed through SeedUse.take, and the analyser compares records with
SeedSpec.expected. Pure standard library."""
from __future__ import annotations


class SeedSpec:
    """Which (block, part) streams an episode samples, and under which inventory key."""

    def __init__(self, blocks, scored, block_key, every_block=("det", "lab"), scored_only=("eval",)):
        self.blocks, self.scored = int(blocks), frozenset(scored)
        self.block_key = block_key
        self.every_block, self.scored_only = tuple(every_block), tuple(scored_only)
        if not self.scored <= set(range(self.blocks)):
            raise ValueError("scored blocks outside the stream")

    def slots(self):
        return [(t, p) for t in range(self.blocks)
                for p in self.every_block + (self.scored_only if t in self.scored else ())]

    @staticmethod
    def name(t, part):
        return f"b{t:02d}:{part}"

    def expected(self, seeds, s, e):
        return {self.name(t, p): int(seeds[self.block_key(s, e, t, p)]) for t, p in self.slots()}


class SeedUse:
    """The runner's side: hands out each planned seed exactly once."""

    def __init__(self, spec, seeds, s, e):
        self.spec, self.plan, self.used = spec, spec.expected(seeds, s, e), {}

    def take(self, t, part):
        k = self.spec.name(t, part)
        if k not in self.plan:
            raise ValueError(f"seed {k} is not in the specification")
        if k in self.used:
            raise ValueError(f"seed {k} used twice")
        self.used[k] = self.plan[k]
        return self.plan[k]

    def finish(self):
        missing = sorted(set(self.plan) - set(self.used))
        if missing:
            raise ValueError(f"planned seeds never used: {missing[:5]}")
        return dict(self.used)
