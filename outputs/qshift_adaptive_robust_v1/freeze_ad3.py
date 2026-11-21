"""Write the non-circular AD3 freeze (AD3_FREEZE.json) before commit (studykit format)."""
from __future__ import annotations

import hashlib

import freeze_ad2
import studykit as SK

AD3 = [f"{SK.PKG}/{n}" for n in (
    "PLAN_AD3.md", "AD3_PROTOCOL.md", "ad3_config.py", "ad3.py", "prepare_ad3.py", "screen_ad3.py",
    "preflight_ad3.py", "freeze_ad3.py", "AD3_SEEDS.json", "AD3_SCREEN.json", "AD3_PREFLIGHT.json",
    "tests/test_ad3.py", "AD2_FREEZE.json")]
# AD3 reuses ad2.py (sampling, estimate, selector, latency rules) and everything AD2 froze; no seal module.
FILES = sorted(set(freeze_ad2.FILES + AD3))


def main() -> None:
    p = SK.write_freeze("AD3", "qshift-adaptive-robust-ad3-freeze-v1",
                        "AD3 faster reaction to a change (development; AD2's public bursts; no seal read)",
                        FILES, "Run AD3")
    print(len(FILES), "files;", hashlib.sha256(p.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
