"""Run existing, unmodified suites against the hotfix.

  python overlay.py <new folder> [codex script]

Copies the traced inputs, the v11 package and the hotfix into a throw-away tree. There, v11's lifecycle11, study11 and
analyze11 become aliases of the hotfix modules; every test file is a byte copy. Then run, from that tree:
  outputs/qshift_decoder_bank_v11/tests/test_v11.py, test_seven.py
  outputs/qshift_decoder_bank_v11_independent_review/ADVERSARIAL_REPRODUCTIONS.py   (if given)
  outputs/qshift_v11_p0_hotfix/tests/test_p0_study.py"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOT, OUT = HERE.parent, HERE.parents[1]
REPO, V11 = OUT.parent, OUT / "qshift_decoder_bank_v11"
SHIM = '''import sys
from pathlib import Path
_h = str(Path(__file__).resolve().parents[1] / "qshift_v11_p0_hotfix")
if _h not in sys.path:
    sys.path.append(_h)
import {new}
sys.modules[__name__] = {new}
'''


def main(dst, codex=None):
    dst = Path(dst).resolve()
    dst.mkdir()
    sys.path.insert(0, str(V11 / "tests"))
    import test_v11 as T
    files = set(T.trace_inputs()) | {f"outputs/qshift_decoder_bank_v9/results/dev/records/{n}.json" for n in T.NAMES}
    files |= set(json.loads((REPO / T.SEED_REL).read_bytes())["screened"]) | {T.SEED_REL, T.TRAIN_REL}
    files |= {p.relative_to(REPO).as_posix() for d in (V11, HOT) for p in d.rglob("*") if p.is_file() and p.suffix != ".pyc"}
    for f in sorted(files):
        (dst / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / f, dst / f)
    for old in ("lifecycle11", "study11"):
        (dst / "outputs/qshift_decoder_bank_v11" / f"{old}.py").write_text(SHIM.format(new=old + "p0"), newline="\n")
    (dst / "outputs/qshift_decoder_bank_v11/analyze11.py").write_text(
        (HOT / "analyze11p0.py").read_text(encoding="utf-8").replace("import study11p0 as S", "import study11 as S")
        .replace("from lifecycle11p0 import", "from lifecycle11 import"), encoding="utf-8", newline="\n")
    if codex:
        d = dst / "outputs/qshift_decoder_bank_v11_independent_review"
        d.mkdir()
        shutil.copyfile(codex, d / "ADVERSARIAL_REPRODUCTIONS.py")
    print(subprocess.run([sys.executable, "-B", "-c", "import sys; sys.path.insert(0, r'%s'); import test_v11 as T; print(T.LC.__name__, T.ST.__name__)"
                          % (dst / "outputs/qshift_decoder_bank_v11/tests")], capture_output=True, text=True, check=True).stdout.strip(), len(files))


if __name__ == "__main__":
    main(*sys.argv[1:])
