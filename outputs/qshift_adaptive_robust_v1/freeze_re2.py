"""Write the non-circular RE2 freeze (RE2_FREEZE.json) before commit (studykit format, as since DEV2)."""
from __future__ import annotations

import hashlib

import freeze_ad1
import studykit as SK

AD1_ONLY = {f"{SK.PKG}/{n}" for n in (
    "PLAN_AD1.md", "AD1_PROTOCOL.md", "ad1_config.py", "ad1_stream.py", "ad1.py", "preflight_ad1.py", "freeze_ad1.py",
    "AD1_PREFLIGHT.json", "tests/test_ad1.py")}
RE2 = [f"{SK.PKG}/{n}" for n in (
    "PLAN_RE2.md", "RE2_PROTOCOL.md", "re2_config.py", "re2_pool.py", "re2_seal.py", "re2_overlap.py",
    "re2_contamination.py", "re2.py", "prepare_re2.py", "preflight_re2.py", "freeze_re2.py", "studykit.py",
    "HIDDEN_COMMITMENT_RE2.json", "RE2_SEEDS.json", "RE2_PREFLIGHT.json", "results/re2/OVERLAP.json",
    "tests/test_re2.py", "HIDDEN_COMMITMENT_RE1.json", "ad1_config.py", "AD1_SEEDS.json")]
# ad1_config.py stays: prepare_ad1 (seed screening) and the distinctness test import it.
FILES = sorted(set([f for f in freeze_ad1.FILES if f not in AD1_ONLY] + RE2))


def main() -> None:
    p = SK.write_freeze("RE2", "qshift-adaptive-robust-re2-freeze-v1",
                        "RE2 frozen evaluation of the E1T pipeline with two new sealed bursts (G1-G5 gated, X2 "
                        "descriptive; RE1's H2 seal not read)", FILES, "Run RE2")
    print(len(FILES), "files;", hashlib.sha256(p.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
