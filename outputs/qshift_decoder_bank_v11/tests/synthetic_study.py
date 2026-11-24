"""A sampler-free synthetic study driven through the real launch, recovery and analysis code. Test use only.

  python synthetic_study.py <repo> <freeze> launch|recover|analyze <run folder> [approved head | output file]

Records are the committed DB8 metadata with seeded synthetic error bits. Every Stim sampler is blocked.
QSHIFT_FAULT="<job>:<fault>" injects one fault."""
from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

V11 = Path(__file__).resolve().parents[1]
for _p in (V11.parents[1], V11.parent / "qshift_decoder_bank_v9", V11.parent / "qshift_decoder_bank_v10", V11, V11 / "tests"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import db8_config as C  # noqa: E402,I001
import numpy as np  # noqa: E402
import analyze11 as A  # noqa: E402
import lifecycle11 as LC  # noqa: E402
import policy as P  # noqa: E402
import study11 as S  # noqa: E402
from strict import SeedUse, loads  # noqa: E402


def block_samplers():
    import stim

    def no(*a, **k):
        raise AssertionError("stim sampler used")
    stim.Circuit.compile_detector_sampler = no
    stim.Circuit.compile_sampler = no
    stim.DetectorErrorModel.compile_sampler = no


block_samplers()


def job(ep, name):
    nm, _, fault = os.environ.get("QSHIFT_FAULT", "").partition(":")
    fault = fault if nm == name else ""
    s, e = name.rsplit("_e", 1)
    ctx = ep.context
    if fault == "infra_once" and len(LC.read_events(ep.log)[0]) == 1:
        raise OSError("before sampling")
    use = SeedUse(P.PLAN.expected(S.frozen_json(ctx, "seeds")["seeds"], s, int(e)))
    r = loads((Path(ctx["repo"]) / f"outputs/qshift_decoder_bank_v9/results/dev/records/{name}.json").read_bytes())
    ep.sampling_intent()
    if fault == "infra_late":
        raise OSError("after intent")
    for t, p in P.PLAN.slots:
        use.take(t, p)
    if fault == "skip_seed":
        use.used.popitem()
    bits, rng = {}, np.random.default_rng(12345)
    for b in r["blocks"]:
        by = {}
        for a in C.ARMS:
            k = b["keys"].get(a, "plain")
            if k not in by:
                by[k] = rng.random(C.EVAL_PER_BLOCK) < 0.01
            bits[f"b{b['block']:02d}_{a}"] = np.packbits(by[k])
            b["errors"][a] = int(by[k].sum())
    used = use.finish()
    ep.sampling_confirmed(used)
    if fault == "die":
        os._exit(7)
    if fault == "sleep":
        time.sleep(120)
    buf = io.BytesIO()
    np.savez_compressed(buf, **bits)
    raw = buf.getvalue()
    if fault == "dup_member":
        import warnings
        import zipfile
        warnings.simplefilter("ignore")
        with zipfile.ZipFile(buf, "a") as z:
            z.writestr("b06_W0F.npy", z.read("b06_W0F.npy"))
        raw = buf.getvalue()
    if fault == "bad_meta":
        r["blocks"][0].update(seg0=-99, L=999)
    if fault == "wrong_seed_meta":
        used = {**used, "b00:det": used["b00:det"] + 1}
    if fault == "partial":
        ep.stage.mkdir()
        (ep.stage / "archive.npz").write_bytes(raw[:100])
        raise OSError("disk error in the middle of the write")
    if fault == "unfrozen_import":
        import types
        m = types.ModuleType("intruder")
        m.__file__ = str(Path(ctx["repo"]) / "intruder.py")
        Path(m.__file__).write_text("x = 1\n")
        sys.modules["intruder"] = m
    r.update(seeds=used, archive="archive.npz")
    ep.commit(r, raw)
    if fault == "damage_commit":
        (ep.final / "COMMIT.json").write_bytes(b"{}")
    if fault == "late_fail":
        raise ValueError("after commit")


def main(repo, freeze, cmd, run, arg=None):
    study = S.Study(repo, freeze)
    if cmd == "launch":
        S.launch(study, run, arg, job, lambda: [("x", "l2", "bad")] if os.environ.get("QSHIFT_FAULT") == ":preflight" else [],
                 on_done=(lambda n: os._exit(9)) if os.environ.get("QSHIFT_FAULT") == ":kill_supervisor" else None)
    elif cmd == "recover":
        LC.recover(run)
    else:
        A.analyze(study, run, arg)


if __name__ == "__main__":
    main(*sys.argv[1:])
