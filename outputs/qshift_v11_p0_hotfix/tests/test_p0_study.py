"""Study-level P0-B tests: the real launch publishes `succeeded` only for runs that analysis admits.

Run only inside the tree built by overlay.py. Synthetic study, samplers blocked."""
from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "qshift_decoder_bank_v11" / "tests"))
import test_v11 as T  # noqa: E402,I001

if T.LC.__name__ != "lifecycle11p0" or T.ST.__name__ != "study11p0":
    raise SystemExit("run this inside the overlay tree")
S, LC = T.S, T.LC


class StudyP0(T.Base):
    setUpClass = classmethod(T.IntegrationTests.setUpClass.__func__)
    tearDownClass = classmethod(T.IntegrationTests.tearDownClass.__func__)
    commit_freeze = classmethod(T.IntegrationTests.commit_freeze.__func__)
    rev = staticmethod(T.IntegrationTests.rev)
    drive, launch, no_analysis = T.IntegrationTests.drive, T.IntegrationTests.launch, T.IntegrationTests.no_analysis

    def test_invalid_study_content_is_never_published_as_success(self):
        """In v11 all three of these launches ended `succeeded`."""
        for fault, why in (("dup_member", "duplicate archive member"), ("bad_meta", "segment start"), ("wrong_seed_meta", "seeds")):
            with self.subTest(fault):
                run = self.tmp / fault
                _, err = self.launch(run=run, fault=f"AA_e0:{fault}", ok=False)
                self.assertIn(why, err)
                c = S.loads((run / "CLOSE.json").read_bytes())
                self.assertEqual((c["outcome"], c["inventory"]["jobs"]["AA_e0"]["state"]), ("failed", "committed"))
                self.assertNotIn("run_end", [x["event"] for x in LC.read_events(run / "journal.jsonl")[0]])
                before = T.snapshot(run)
                for _ in range(2):
                    self.no_analysis(run=run)
                    with self.assertRaises(LC.RunStop):
                        LC.recover(run)
                self.assertEqual(before, T.snapshot(run))

    def test_study_changed_during_the_run(self):
        """A frozen file edited while the run is in progress: no success."""
        repo = self.tmp / "repo2"
        shutil.copytree(self.repo, repo)
        p = self.drive("launch", arg=self.head, repo=repo, wait=False)
        end = T.time.monotonic() + 60
        while not (self.run_dir / "START.json").exists() and T.time.monotonic() < end:
            T.time.sleep(0.05)
        f = repo / "outputs/qshift_decoder_bank_v2/db2_core.py"
        f.write_bytes(f.read_bytes() + b"# edit\n")
        _, err = p.communicate(timeout=300)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(S.loads((self.run_dir / "CLOSE.json").read_bytes())["outcome"], "failed", err[-500:])
        self.no_analysis()

    def test_success_is_admitted(self):
        self.launch()
        out = self.tmp / "A.json"
        self.drive("analyze", arg=str(out))
        self.assertEqual(len(S.loads(out.read_bytes())["episodes"]), 64)


if __name__ == "__main__":
    unittest.main()
