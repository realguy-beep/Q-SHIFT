"""One-command package check: every freeze still matches the tree, and every test file passes.

    python outputs/qshift_adaptive_robust_v1/check_package.py

Each test file runs in its own interpreter. Several frozen packages ship a module named `contract.py`; once one is
imported, `sys.modules` serves it to the others, so running all test files in one process fails the RE1 and DEV2
seed-screen tests even though each file passes alone. Separate processes avoid that without editing frozen tests.
No sampling, no decoding beyond what the tests themselves do.
"""
from __future__ import annotations

import subprocess
import sys
import time

import studykit as K


def main() -> int:
    ok = True
    for fz in sorted(K.ROOT.glob("*_FREEZE.json")):
        bad = K.check_freeze(fz)
        ok &= not bad
        print(f"{fz.name}: {'intact' if not bad else 'CHANGED ' + ', '.join(bad)}")
    for t in sorted((K.ROOT / "tests").glob("test_*.py")):
        t0 = time.time()
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(t.parent), "-p", t.name],
                           cwd=K.REPO, capture_output=True, text=True)
        last = (r.stderr.strip().splitlines() or ["?"])[-1]
        summary = next((ln for ln in reversed(r.stderr.splitlines()) if ln.startswith("Ran ")), "")
        ok &= r.returncode == 0
        print(f"{t.name}: {last} ({summary.removeprefix('Ran ')}, {time.time() - t0:.0f} s)")
        if r.returncode:
            print(r.stderr[-3000:])
    print("ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
