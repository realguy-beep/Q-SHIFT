"""Strict input parsing: JSON, seed inventories and NPZ archives (v10 review, blocker 4). No sampling."""
from __future__ import annotations

import hashlib
import io
import json
import zipfile

import numpy as np

SEED_MIN, SEED_MAX = 1, 2 ** 31 - 1          # the range every Q-SHIFT inventory has been derived in


class Invalid(ValueError):
    pass


def need(ok, what):
    if not ok:
        raise Invalid(what)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def jbytes(obj):
    return (json.dumps(obj, indent=1, sort_keys=True, allow_nan=False) + "\n").encode()


# ------------------------------------------------------------------ JSON
def _pairs(kv):
    d = dict(kv)
    need(len(d) == len(kv), "duplicate JSON key")
    return d


def _const(x):
    raise Invalid(f"non-finite JSON number {x}")


def loads(b):
    """JSON without duplicate keys, NaN or infinities."""
    try:
        return json.loads(b, object_pairs_hook=_pairs, parse_constant=_const)
    except Invalid:
        raise
    except (ValueError, RecursionError) as ex:
        raise Invalid(f"bad JSON: {ex}") from None


def same(a, b):
    """Equality that does not mix types: 1, 1.0 and True are all different."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(map(same, a, b))
    return a == b


def is_int(v, lo=None, hi=None):
    return type(v) is int and (lo is None or v >= lo) and (hi is None or v <= hi)


def is_num(v):
    return type(v) in (int, float) and v == v and abs(v) != float("inf")


# ------------------------------------------------------------------ seeds
def check_seed(v, what="seed"):
    need(is_int(v, SEED_MIN, SEED_MAX), f"{what}: {v!r} is not an integer in [{SEED_MIN}, {SEED_MAX}]")
    return v


def check_inventory(seeds, expected_keys, reserved=()):
    """Exact key set, exact integer types and range, unique across the whole inventory and against `reserved` values."""
    need(isinstance(seeds, dict), "seed inventory is not an object")
    keys = list(expected_keys)
    need(len(set(keys)) == len(keys), "expected seed keys repeat")
    need(set(seeds) == set(keys), "seed inventory keys")
    for k, v in seeds.items():
        check_seed(v, k)
    need(len(set(seeds.values())) == len(seeds), "seed value used twice in the inventory")
    need(not set(reserved) & set(seeds.values()), "seed value already used by an earlier study")
    return seeds


class SeedPlan:
    """The seeds one episode must use; shared by the runner (take/finish) and admission (expected)."""

    def __init__(self, blocks, scored, block_key, every_block=("det", "lab"), scored_only=("eval",)):
        need(set(scored) <= set(range(blocks)), "scored blocks outside the stream")
        self.slots = [(t, p) for t in range(blocks) for p in (*every_block, *(scored_only if t in set(scored) else ()))]
        self.block_key = block_key

    def expected(self, seeds, s, e):
        out = {f"b{t:02d}:{p}": check_seed(seeds[self.block_key(s, e, t, p)]) for t, p in self.slots}
        need(len(set(out.values())) == len(out) == len(self.slots), f"{s}_e{e}: seed slots alias")
        return out


class SeedUse:
    def __init__(self, expected):
        self.plan, self.used = dict(expected), {}

    def take(self, t, part):
        k = f"b{t:02d}:{part}"
        need(k in self.plan, f"seed {k} is not planned")
        need(k not in self.used, f"seed {k} used twice")
        self.used[k] = self.plan[k]
        return self.plan[k]

    def finish(self):
        need(self.used == self.plan, "planned seeds never used")
        return dict(self.used)


# ------------------------------------------------------------------ archives
def read_archive(raw, names, rows):
    """-> {name: bool[rows]}. One plain member per name, exact npy header, zero padding, nothing else in the file."""
    width, names = -(-rows // 8), list(names)
    need(len(set(names)) == len(names), "expected archive names repeat")
    out = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            infos = z.infolist()
            got = [i.filename for i in infos]
            need(len(set(got)) == len(got), "duplicate archive member")
            need(set(got) == {n + ".npy" for n in names}, "archive members")
            need(not z.comment and min(i.header_offset for i in infos) == 0, "archive framing")
            for i in infos:
                need(not i.flag_bits & 1 and i.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                     f"{i.filename}: encoding")
                need(i.file_size <= 4096 + width, f"{i.filename}: size")
                f = io.BytesIO(z.read(i))
                need(np.lib.format.read_magic(f) == (1, 0), f"{i.filename}: npy version")
                shape, fortran, dtype = np.lib.format.read_array_header_1_0(f)
                need(shape == (width,) and not fortran and dtype == np.uint8, f"{i.filename}: shape or type")
                body = f.read()
                need(len(body) == width, f"{i.filename}: length")
                bits = np.unpackbits(np.frombuffer(body, np.uint8))
                need(not bits[rows:].any(), f"{i.filename}: padding")
                out[i.filename[:-4]] = bits[:rows].astype(bool)
    except Invalid:
        raise
    except Exception as ex:      # noqa: BLE001  (any malformed container is invalid input)
        raise Invalid(f"unreadable archive: {ex!r}") from None
    return out
