"""Sampler-free adversarial probes. Every write is inside a temporary synthetic run."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier, Event, Thread, current_thread
from unittest.mock import patch
import json
import os
import subprocess
import sys
import time
import warnings
import zipfile

import numpy as np
import runkit2 as R

HEAD, FREEZE = "a"*40, "b"*64
NAME = "AA_e0"


def setup(path):
    reservation = R.reserve(path, HEAD, FREEZE, [NAME], 1)
    for k in ("events", "episodes", "staging", "partial"):
        (path / k).mkdir()
    return reservation


def worker(path, phase):
    reservation = R.read_reservation(path)
    ep = R.Episode(path, reservation["run_id"], NAME)
    ep.sampling()
    if phase == "writing":
        ep.stage.mkdir()
        R.write_new(ep.stage/"archive.npz", b"interrupted synthetic payload")
    else:
        rename = os.rename

        def after_rename(src, dst):
            rename(src, dst)
            R.write_new(path/"probe-ready", b"")
            time.sleep(120)

        with patch.object(R.os, "rename", after_rename):
            ep.commit({}, b"complete synthetic payload")
    R.write_new(path/"probe-ready", b"")
    time.sleep(120)


def real_crash(path, phase):
    rid = setup(path)["run_id"]
    proc = subprocess.Popen([sys.executable, "-B", __file__, "--worker", str(path), phase])
    try:
        deadline = time.monotonic()+15
        while not (path/"probe-ready").exists():
            if proc.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError(f"synthetic child failed to reach {phase}")
            time.sleep(.025)
        proc.kill()
        proc.wait(timeout=15)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=15)
    log = path/"events"/f"{NAME}.jsonl"
    with log.open("ab") as f:
        f.write(b'{"event":')  # torn tail at simulated append boundary
    result = R.recover(path)["jobs"][NAME]
    assert result["torn_event_line"]
    if phase == "writing":
        assert result["state"] == "partial"
        assert (path/"staging"/NAME/"archive.npz").read_bytes() == b"interrupted synthetic payload"
    else:
        assert result["state"] == "committed" and "committed" not in result["events"]
        assert R.read_committed(path, rid, NAME)[1] == b"complete synthetic payload"
    print("PASS", phase, "real process termination, retained bytes, correct recovery class")


def bad_recovery(path):
    rid = setup(path)["run_id"]
    (path/"episodes"/NAME).mkdir()
    out = R.recover(path)
    assert out["jobs"][NAME]["state"] == "committed"
    try:
        R.read_committed(path, rid, NAME)
    except ValueError:
        print("GAP recovery labels an empty episode directory committed")
    else:
        raise AssertionError("invalid commit accepted by read_committed")


def job(run, rid, name, _):
    ep = R.Episode(run, rid, name)
    ep.sampling()
    return ep.commit({}, b"synthetic")


def closed_start(path):
    reservation = R.reserve(path, HEAD, FREEZE, [NAME], 1)
    R.recover(path)
    st = R.run_jobs([(NAME, None)], job, path, reservation, executor=ThreadPoolExecutor)
    assert st["state"] == "ready_for_analysis" and (path/"RECOVERY.json").exists()
    print("GAP recovered reservation with no status admits a fresh start")


def competing_starts(path):
    res = R.reserve(path, HEAD, FREEZE, [NAME], 1)
    startup = Barrier(2)
    a_has_dirs, b_done = Event(), Event()
    orig = R._dump
    outputs = {}

    def hooked_dump(p, obj):
        if p.name == "RUN_STATUS.json" and obj["state"] == "starting":
            startup.wait(timeout=8)
            if current_thread().name == "B":
                assert a_has_dirs.wait(8)
        return orig(p, obj)

    def factory():
        a_has_dirs.set()
        assert b_done.wait(8)
        return ThreadPoolExecutor(max_workers=1)

    def start():
        label = current_thread().name
        try:
            outputs[label] = R.run_jobs([(NAME, None)], job, path, res,
                                        executor=factory if label == "A" else ThreadPoolExecutor)
        except BaseException as ex:
            outputs[label] = ex
        finally:
            if label == "B":
                b_done.set()

    with patch.object(R, "_dump", side_effect=hooked_dump), patch.object(R, "now", return_value="2030-01-01T00:00:00Z"):
        threads = [Thread(name=x, target=start) for x in "AB"]
        for t in threads:
            t.start()
        for t in threads:
            t.join(20)
        assert not any(t.is_alive() for t in threads)
    assert outputs["A"]["state"] == "ready_for_analysis" and isinstance(outputs["B"], FileExistsError)
    assert (path/"FAILURE.json").is_file()
    e, _ = R.read_events(path/"journal.jsonl")
    assert [x["event"] for x in e].count("run_start") == 2
    print("GAP competing starts consume one reservation and leave ready status plus FAILURE")


def semantic_and_bound(path):
    import validate as V

    seeds, tr = V.db8_seeds(), V.training()
    r = json.loads((V.C.ROOT/"results/dev/records/AA_e0.json").read_bytes())
    args = (seeds, tr, ("AA", 0))
    V.validate_record(r, *args)
    b = deepcopy(r)
    b["blocks"][0].update(plausible=["NOT_A_BANK_STATE"], estimate="invalid", seg0=-99, L=999)
    b["changes_detected"] = [-1, 999]
    V.validate_record(b, *args)
    print("GAP contradictory plausible states, estimate and segment history accepted")

    b = deepcopy(r)
    for block in b["blocks"]:
        block["errors"] = dict.fromkeys(V.C.ARMS, 0)
    # Format-valid arrays that do not contain any measured outcomes.
    raw = BytesIO()
    np.savez(raw, **{f"b{t:02d}_{a}": np.zeros(125, np.uint8)
                     for t in V.C.SCORED for a in V.C.ARMS})
    pure = raw.getvalue()
    rid = setup(path)["run_id"]
    ep = R.Episode(path, rid, NAME)
    ep.sampling()
    ep.commit(b, pure)
    s = dict(state="ready_for_analysis", run_id=rid, head=HEAD, freeze_sha256=FREEZE,
             jobs={NAME: {"returncode": 0, "rerun": False}}, reruns={})
    R.write_new(path/"RUN_STATUS.json", R.jbytes(s))
    j = path/"journal.jsonl"
    R.append_event(j, "run_start", run_id=rid)
    R.append_event(j, "run_failed", error="injected")
    R.append_event(j, "job_done", job=NAME)
    R.append_event(j, "run_end", state="failed")
    with patch.object(V.C, "EPISODES", {"AA":1}):
        V.load_bound(path, HEAD, FREEZE)
        print("GAP bound loader accepts run_failed and a failed terminal journal")
    malformed = BytesIO(pure)
    member = "b06_W0F.npy"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(malformed, "a") as z:
            z.writestr(member, z.read(member))
    b["archive_sha256"] = R.sha(malformed.getvalue())
    V.arrays(b, malformed.getvalue())
    print("GAP byte-valid archive with duplicate member accepted")


def seed_alias():
    from seed_spec import SeedSpec, SeedUse

    ss = SeedSpec(1, (), lambda _s, _e, _t, p: p)
    su = SeedUse(ss, {"det": 4.9, "lab": 4}, "test", 0)
    assert su.take(0, "det") == su.take(0, "lab") == 4
    su.finish()
    print("GAP seed aliasing and fractional coercion admitted by stand-alone spec")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--worker"]:
        worker(Path(sys.argv[2]), sys.argv[3])
    else:
        if not __debug__:
            raise RuntimeError("Run with assertions enabled")
        root = Path(sys.argv[1]).resolve()
        sys.path.extend((str(root), str(root / "outputs/qshift_decoder_bank_v9")))
        import stim

        def blocked(*args, **kwargs):
            raise AssertionError("Stim sampler requested by adversarial fixture")

        stim.Circuit.compile_detector_sampler = blocked
        stim.Circuit.compile_sampler = blocked
        stim.DetectorErrorModel.compile_sampler = blocked
        with TemporaryDirectory() as tmp:
            p = Path(tmp)
            real_crash(p/"writing", "writing")
            real_crash(p/"renamed", "renamed")
            bad_recovery(p/"corrupt")
            closed_start(p/"recovered")
            competing_starts(p/"concurrent")
            semantic_and_bound(p/"inconsistent")
            seed_alias()
