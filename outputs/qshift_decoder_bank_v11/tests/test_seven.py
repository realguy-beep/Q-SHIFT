"""Codex's seven reproduced v10 failures (audit_v10_adversarial.py at e9b89bbf1), ported to the v11 interfaces.

Each test performs the same abuse and requires v11 to fail closed. No Stim sampling."""
from __future__ import annotations

import copy
import io
import json
import sys
import threading
import unittest
import warnings
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_v11 as T  # noqa: E402,I001
from test_v11 import C, LC, P, S  # noqa: E402


class Seven(T.Base):
    def base(self):
        return S.loads((C.ROOT / "results/dev/records/AA_e0.json").read_bytes())

    def pure(self):
        f = io.BytesIO()
        np.savez(f, **{f"b{t:02d}_{a}": np.zeros(125, np.uint8) for t in C.SCORED for a in C.ARMS})
        return f.getvalue()

    def test_1_empty_episode_directory_is_not_committed(self):
        LC.reserve(self.run_dir, {}, ["a"], 1)
        (self.run_dir / "episodes/a").mkdir()
        self.assertEqual(LC.recover(self.run_dir)["inventory"]["jobs"]["a"]["state"], "corrupt")

    def test_2_recovered_reservation_cannot_start(self):
        res = LC.reserve(self.run_dir, {}, ["a"], 1)
        LC.recover(self.run_dir)
        with self.assertRaises(LC.StartRefused):
            LC.execute(res, [("a", None)], T.tiny)
        self.assertEqual(json.loads((self.run_dir / "CLOSE.json").read_bytes())["outcome"], "recovered")

    def test_3_competing_starts(self):
        """Both callers are released together after the winner's claim is already possible; repeated."""
        for k in range(20):
            run = self.tmp / f"r{k}"
            res = LC.reserve(run, {}, ["a"], 1)
            gate, got = threading.Barrier(2), []

            def start():
                gate.wait(8)
                try:
                    got.append(LC._claim(res))
                except LC.StartRefused as ex:
                    got.append(ex)
            th = [threading.Thread(target=start) for _ in range(2)]
            [t.start() for t in th]
            [t.join(20) for t in th]
            self.assertEqual(sorted(type(x).__name__ for x in got), ["Lock", "StartRefused"])
            self.assertEqual({p.name for p in run.iterdir()}, {"RUN.json", "START.json", *LC.DIRS})
            next(x for x in got if isinstance(x, LC.Lock)).close()
            with self.assertRaises(LC.StartRefused):
                LC.execute(res, [("a", None)], T.tiny, pool=lambda: ThreadPoolExecutor(1))
            self.assertFalse((run / "CLOSE.json").exists() or (run / "journal.jsonl").exists())

    def test_4_contradictory_metadata(self):
        b = self.base()
        P.check_record(b, T.SEEDS, T.TR, ("AA", 0))
        whole = copy.deepcopy(b)
        whole["blocks"][0].update(plausible=["NOT_A_BANK_STATE"], estimate="invalid", seg0=-99, L=999)
        whole["changes_detected"] = [-1, 999]
        parts = [whole]
        for k, v in (("plausible", ["NOT_A_BANK_STATE"]), ("estimate", "invalid"), ("seg0", -99), ("L", 999)):
            x = copy.deepcopy(b)
            x["blocks"][0][k] = v
            parts.append(x)
        x = copy.deepcopy(b)
        x["changes_detected"] = [-1, 999]
        for y in (*parts, x):
            with self.assertRaises(S.Invalid):
                P.check_record(y, T.SEEDS, T.TR, ("AA", 0))

    def test_5_failed_journal_is_not_admitted(self):
        res = LC.reserve(self.run_dir, {}, ["AA_e0"], 1)
        LC.execute(res, [("AA_e0", None)], T.tiny)
        LC.load_success(self.run_dir)
        e = LC.read_events(self.run_dir / "journal.jsonl")[0]
        e.insert(-1, {"t": e[-1]["t"], "event": "run_failed", "error": "injected"})
        e[-1]["state"] = "failed"
        (self.run_dir / "journal.jsonl").write_bytes(T.rechain(e))
        self.rejected()
        T.reclose(self.run_dir)                                              # CLOSE.json still says succeeded
        self.rejected()

    def test_6_duplicate_archive_member(self):
        r = self.base()
        for b in r["blocks"]:
            b["errors"] = dict.fromkeys(C.ARMS, 0)
        P.check_arrays(r, self.pure())
        f = io.BytesIO(self.pure())
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with zipfile.ZipFile(f, "a") as z:
                z.writestr("b06_W0F.npy", z.read("b06_W0F.npy"))
        with self.assertRaisesRegex(S.Invalid, "duplicate archive member"):
            P.check_arrays(r, f.getvalue())

    def test_7_seed_alias(self):
        pl = S.SeedPlan(1, (), lambda _s, _e, _t, p: p)
        for seeds in ({"det": 4.9, "lab": 4}, {"det": 4, "lab": 4}):
            with self.assertRaises(S.Invalid):
                pl.expected(seeds, "test", 0)


if __name__ == "__main__":
    unittest.main()
