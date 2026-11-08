"""Real subprocess fixture for ownership handoff and orphan tests (Windows)."""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from ownership_runtime_v4 import (RunDirectoryLock, ChildOwnership, Deadline, WindowsChildJob,
    start_deadline_watchdog, publish_child_intent, record_child_spawn,
    assert_child_ownership_clear, atomic_json, LockBusyError)


def child(args):
    complete=__import__('threading').Event()
    start_deadline_watchdog(args.qshift_deadline_monotonic,complete,args.role+'-bootstrap')
    if args.ready_marker: Path(args.ready_marker).write_text('preclaim',encoding='utf-8')
    if args.preclaim_delay: time.sleep(args.preclaim_delay)
    with ChildOwnership(args.run_dir,args.role,args.qshift_owner_token,args.qshift_deadline_monotonic):
        Path(args.active_marker).write_text('owned',encoding='utf-8')
        while True: time.sleep(.05)


def supervisor(args):
    run=Path(args.run_dir); deadline=time.monotonic()+args.child_lifetime
    job=WindowsChildJob()
    try:
      with RunDirectoryLock(run,kind='launcher'):
        assert_child_ownership_clear(run)
        token=publish_child_intent(run,args.role,deadline)
        ready=Path(args.ready_marker)
        child_ready=Path(args.child_ready_marker)
        command=[sys.executable,str(Path(__file__).resolve()),'--child','--run-dir',str(run),
          '--role',args.role,'--active-marker',str(args.active_marker),'--ready-marker',str(child_ready),
          '--preclaim-delay',str(args.preclaim_delay),f'--qshift-owner-token={token}',
          f'--qshift-deadline-monotonic={deadline:.17g}']
        proc=job.create_suspended(command,cwd=HERE,env=os.environ.copy(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if args.hold_suspended:
            atomic_json(ready,{'token':token,'child_pid':proc.pid,'role':args.role,'deadline':deadline})
            while True: time.sleep(.05)
        job.assign(proc)
        record_child_spawn(run,token,proc.pid)
        atomic_json(ready,{'token':token,'child_pid':proc.pid,'role':args.role,'deadline':deadline})
        job.resume(proc)
        if args.delay_record: time.sleep(args.delay_record)
        while proc.poll() is None: time.sleep(.05)
    finally:
        job.close()


def probe(args):
    try:
        with RunDirectoryLock(args.run_dir,kind='launcher'):
            outcome=assert_child_ownership_clear(args.run_dir)
        print(json.dumps({'status':'PASS','ownership':outcome},sort_keys=True))
        return 0
    except LockBusyError:
        return 12


def watchdog_only(args):
    complete=__import__('threading').Event()
    deadline=time.monotonic()+args.watchdog_seconds
    start_deadline_watchdog(deadline,complete,'watchdog-expiry-test')
    while True: time.sleep(.05)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--child',action='store_true'); parser.add_argument('--supervisor',action='store_true')
    parser.add_argument('--probe',action='store_true')
    parser.add_argument('--watchdog-only',action='store_true')
    parser.add_argument('--watchdog-seconds',type=float,default=0.5)
    parser.add_argument('--run-dir',type=Path,required=True); parser.add_argument('--role',choices=('worker','auditor','finalizer'),default='auditor')
    parser.add_argument('--active-marker',type=Path); parser.add_argument('--ready-marker',type=Path)
    parser.add_argument('--child-ready-marker',type=Path); parser.add_argument('--preclaim-delay',type=float,default=0)
    parser.add_argument('--delay-record',type=float,default=0); parser.add_argument('--child-lifetime',type=float,default=3.2)
    parser.add_argument('--hold-suspended',action='store_true')
    parser.add_argument('--qshift-owner-token',default=None); parser.add_argument('--qshift-deadline-monotonic',type=float,default=None)
    args=parser.parse_args()
    if args.child: return child(args)
    if args.supervisor: return supervisor(args)
    if args.probe: return probe(args)
    if args.watchdog_only: return watchdog_only(args)
    parser.error('select --child, --supervisor, or --probe')

if __name__=='__main__': raise SystemExit(main())
