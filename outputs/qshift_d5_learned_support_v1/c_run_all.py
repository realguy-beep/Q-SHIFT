"""Phase C launcher: the two calibration (learning) jobs, then every root job; single attempt, no retry.

Usage: c_run_all.py <mode> <run_dir> [--expected-head SHA] [--workers 8] [--open-hidden-seal]
Eval mode requires a clean tree, HEAD == --expected-head and --open-hidden-seal (owner authorization).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
import c_contract as K  # noqa: E402

JOB_TIMEOUT_S = 3_600


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    mode, run_dir = sys.argv[1], Path(sys.argv[2]).resolve()
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    head = sys.argv[sys.argv.index("--expected-head") + 1] if "--expected-head" in sys.argv else None
    alloc = K.MODES[mode]
    if mode == "eval":
        if head is None or git("rev-parse", "HEAD") != head:
            raise SystemExit("eval mode requires --expected-head equal to HEAD")
        if git("status", "--porcelain"):
            raise SystemExit("eval mode requires a clean tree")
        if "--open-hidden-seal" not in sys.argv:
            raise SystemExit("eval mode requires --open-hidden-seal (owner authorization to open H's seal)")
    status_path = run_dir / "RUN_STATUS.json"
    if status_path.exists():
        raise SystemExit("RUN_STATUS.json exists; single attempt only")
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    jobs = K.jobs(alloc)
    status = {"mode": mode, "allocation": alloc.as_dict(), "head": git("rev-parse", "HEAD"), "expected_head": head,
              "hidden_seal_opened": mode == "eval", "started": now(), "workers": workers, "state": "running",
              "calibration": {}, "jobs": {}}

    def save():
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8", newline="\n")

    save()
    extra = (["--expected-head", head] if head else []) + (["--open-hidden-seal"] if mode == "eval" else [])

    def launch(args, name):
        t = time.perf_counter()
        with open(run_dir / "logs" / f"{name}.log", "w", encoding="utf-8") as log:
            try:
                rc = subprocess.run([sys.executable, str(ROOT / "c_job.py"), *args, *extra], cwd=REPO, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=JOB_TIMEOUT_S).returncode
            except subprocess.TimeoutExpired:
                rc = -9
        return name, rc, time.perf_counter() - t

    with ThreadPoolExecutor(max_workers=2) as pool:
        for s, rc, sec in pool.map(lambda c: launch(["calibrate", mode, c, str(run_dir)], f"calibrate_{c}"),
                                   K.CONDITIONS):
            status["calibration"][s] = {"returncode": rc, "seconds": round(sec, 1)}
            print(s, rc, round(sec, 1), flush=True)
    save()
    if any(v["returncode"] != 0 for v in status["calibration"].values()):
        status.update(state="failed", finished=now())
        save()
        raise SystemExit("calibration failed")

    def one(job):
        c, qi, r = job
        return launch(["root", mode, c, str(qi), str(r), str(run_dir)], K.stem(c, qi, r))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for s, rc, sec in pool.map(one, jobs):
            status["jobs"][s] = {"returncode": rc, "seconds": round(sec, 1)}
            save()
            print(s, rc, round(sec, 1), flush=True)
    ok = len(status["jobs"]) == len(jobs) and all(j["returncode"] == 0 for j in status["jobs"].values())
    status.update(state="ready_for_analysis" if ok else "failed", finished=now())
    save()
    print("STATE", status["state"], flush=True)


if __name__ == "__main__":
    main()
