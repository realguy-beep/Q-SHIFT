"""Small shared helpers for V1.6b (no sampler, no decoder construction)."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
CONFIG_PATH = ROOT / "config.json"
COMMITMENT_PATH = REPO / "outputs" / "qshift_correlated_decoder_v1_6" / "HIDDEN_BURST_COMMITMENT.json"
SEALED_DEFAULT = REPO.parents[1] / "qshift_v1_6_hidden_burst_SEALED.json"   # Documents/Codex/, outside git


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def atomic_json(path: Path, value) -> None:
    atomic_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def atomic_npz(path: Path, **arrays) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    raw = path.read_bytes()
    return sha256_bytes(raw), len(raw)


def canonical(plaintext: dict) -> bytes:
    """Must match outputs/qshift_correlated_decoder_v1_6/seal_hidden_burst.py."""
    return json.dumps(plaintext, sort_keys=True, separators=(",", ":")).encode("utf-8")


def open_hidden_support(sealed_path: Path, commitment_path: Path = COMMITMENT_PATH) -> tuple[int, ...]:
    """Verify the sealed plaintext against the committed SHA-256; only then return the support."""
    commitment = load_json(commitment_path)
    plaintext = load_json(sealed_path)
    if sha256_bytes(canonical(plaintext)) != commitment["sha256_of_canonical_plaintext"]:
        raise RuntimeError("hidden burst plaintext does not match the committed hash")
    support = tuple(int(v) for v in plaintext["support"])
    if not 1 <= len(support) <= 3 or len(set(support)) != len(support):
        raise RuntimeError("hidden burst support is malformed")
    return support
