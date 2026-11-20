"""Write the non-circular AD2 freeze (AD2_FREEZE.json) before commit (studykit format)."""
from __future__ import annotations

import hashlib

import freeze_re2
import studykit as SK

RE2_ONLY = {f"{SK.PKG}/{n}" for n in (
    "PLAN_RE2.md", "RE2_PROTOCOL.md", "re2_config.py", "re2_pool.py", "re2_seal.py", "re2_overlap.py",
    "re2_contamination.py", "re2.py", "preflight_re2.py", "freeze_re2.py", "HIDDEN_COMMITMENT_RE2.json",
    "RE2_PREFLIGHT.json", "results/re2/OVERLAP.json", "tests/test_re2.py", "HIDDEN_COMMITMENT_RE1.json",
    "re1_seal.py")}   # AD2 imports no seal code
AD2 = [f"{SK.PKG}/{n}" for n in (
    "PLAN_AD2.md", "AD2_PROTOCOL.md", "ad2_config.py", "ad2.py", "prepare_ad2.py", "preflight_ad2.py", "freeze_ad2.py",
    "AD2_SEEDS.json", "AD2_PREFLIGHT.json", "tests/test_ad2.py", "studykit.py",
    "ad1.py", "ad1_config.py", "ad1_stream.py", "AD1_SEEDS.json", "prepare_ad1.py",
    "prepare_re2.py", "RE2_SEEDS.json", "re2_config.py", "BRS_BURSTS.json", "BRT_BURSTS.json")]
# re2_config stays: prepare_re2 (seed screening) imports it. ad1* stay: AD2 reuses ad1.estimate_window.
FILES = sorted(set([f for f in freeze_re2.FILES if f not in RE2_ONLY] + AD2))


def main() -> None:
    p = SK.write_freeze("AD2", "qshift-adaptive-robust-ad2-freeze-v1",
                        "AD2 adaptive decoding when the burst itself changes (development; public bursts; no seal read)",
                        FILES, "Run AD2")
    print(len(FILES), "files;", hashlib.sha256(p.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
