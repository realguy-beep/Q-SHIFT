"""Opt-in, low-volume benchmark harness for safety tests only."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from safety_runner_v3 import safe_execute

HERE=Path(__file__).resolve().parent
def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',type=Path,default=HERE/'benchmark_config.json')
    ap.add_argument('--run-dir',type=Path,required=True)
    ap.add_argument('--recover-uncommitted',action='store_true')
    ap.add_argument('--fault')
    ap.add_argument('--kill-active-sampler',action='store_true')
    a=ap.parse_args(argv)
    result=safe_execute(a.run_dir,timeout_seconds=120,benchmark_config=a.config.resolve(),
                        recover_uncommitted=a.recover_uncommitted,test_fault=a.fault,
                        kill_on_sample_marker=a.kill_active_sampler)
    print(json.dumps(result,indent=2,default=str))
    return 0 if result['status']=='completed' else 3
if __name__=='__main__': raise SystemExit(main())
