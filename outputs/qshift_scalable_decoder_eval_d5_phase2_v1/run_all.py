"""Launch every root job for a mode, at most WORKERS at once; single attempt, no retry.

Usage: run_all.py <mode> <run_dir> [--expected-head SHA] [--workers 8]
Eval mode additionally requires a clean git tree and HEAD == --expected-head before any job starts.
Writes <run_dir>/RUN_STATUS.json (state: running -> ready_for_analysis | failed) and per-job logs.
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
import contract as K  # noqa: E402

JOB_TIMEOUT_S = 3_600   # per root job; the preflight projects about 7 min


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
    status_path = run_dir / "RUN_STATUS.json"
    if status_path.exists():
        raise SystemExit("RUN_STATUS.json exists; single attempt only")
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    jobs = [(qi, r) for qi in range(len(K.QS)) for r in range(alloc.roots_per_q)]
    status = {"mode": mode, "allocation": alloc.as_dict(), "head": git("rev-parse", "HEAD"), "expected_head": head,
              "started": now(), "workers": workers, "state": "running", "jobs": {}}
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8", newline="\n")

    def one(job):
        qi, r = job
        cmd = [sys.executable, str(ROOT / "eval_job.py"), mode, str(qi), str(r), str(run_dir)]
        if head:
            cmd += ["--expected-head", head]
        t = time.perf_counter()
        with open(run_dir / "logs" / f"{K.stem(qi, r)}.log", "w", encoding="utf-8") as log:
            try:
                rc = subprocess.run(cmd, cwd=REPO, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=JOB_TIMEOUT_S).returncode
            except subprocess.TimeoutExpired:
                rc = -9  # recorded as a failure; no retry
        return K.stem(qi, r), rc, time.perf_counter() - t

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for s, rc, sec in pool.map(one, jobs):
            status["jobs"][s] = {"returncode": rc, "seconds": round(sec, 1)}
            status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8", newline="\n")
            print(s, rc, round(sec, 1), flush=True)
    ok = len(status["jobs"]) == len(jobs) and all(j["returncode"] == 0 for j in status["jobs"].values())
    status.update(state="ready_for_analysis" if ok else "failed", finished=now())
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("STATE", status["state"], flush=True)


if __name__ == "__main__":
    main()
