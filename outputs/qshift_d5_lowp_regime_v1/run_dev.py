"""Stage S launcher: 6 sample jobs, then 18 L2 jobs (2 conditions x 3 q x 3 priors), at most 8 at once.

Usage: run_dev.py [--rehearse]   (non-rehearsal requires a clean tree with DEV_SEEDS.json committed)
"""
from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
import contract as K  # noqa: E402


def run(args, name, rehearse):
    logs = ROOT / "work" / ("dev_rehearsal_logs" if rehearse else "dev_logs")
    logs.mkdir(parents=True, exist_ok=True)
    with open(logs / f"{name}.log", "w", encoding="utf-8") as log:
        rc = subprocess.run([sys.executable, str(ROOT / "dev_jobs.py"), *args] + (["--rehearse"] if rehearse else []),
                            cwd=REPO, stdout=log, stderr=subprocess.STDOUT).returncode
    print(name, rc, flush=True)
    return rc


def main() -> None:
    rehearse = "--rehearse" in sys.argv
    if not rehearse:
        if subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True).stdout.strip():
            raise SystemExit("Stage S requires a clean tree")
        if subprocess.run(["git", "ls-files", "--error-unmatch", "outputs/qshift_d5_lowp_regime_v1/DEV_SEEDS.json"],
                          cwd=REPO, capture_output=True).returncode:
            raise SystemExit("DEV_SEEDS.json must be committed")
    cells = [(c, qi) for c in K.CONDITIONS for qi in range(len(K.QS))]
    with ThreadPoolExecutor(max_workers=8) as pool:
        rcs = list(pool.map(lambda a: run(["sample", a[0], str(a[1])], f"sample_{a[0]}_q{a[1]}", rehearse), cells))
        if any(rcs):
            raise SystemExit("sampling failed")
        l2 = sorted([(c, qi, pr) for c, qi in cells for pr in K.L2_PRIORS], key=lambda a: -K.CONDITIONS[a[0]][1])
        rcs = list(pool.map(lambda a: run(["l2", a[0], str(a[1]), str(a[2])], f"l2_{a[0]}_q{a[1]}_{a[2]}", rehearse), l2))
    print("STATE", "done" if not any(rcs) else "failed")


if __name__ == "__main__":
    main()
