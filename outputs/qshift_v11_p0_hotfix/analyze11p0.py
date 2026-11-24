"""Analysis entry point: admission first, then DB8's frozen criteria through v10's analyze10.

  python analyze11p0.py <repo> <freeze path in repo> <run folder> <new output file>

There is no way to pass records in: an unadmitted run raises before anything is computed or written."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _p in (_ROOT.parents[1], _ROOT.parent / "qshift_decoder_bank_v9", _ROOT.parent / "qshift_decoder_bank_v10",
           _ROOT.parent / "qshift_decoder_bank_v11", _ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import db8_config  # noqa: E402,F401,I001
import analyze10 as A10  # noqa: E402
import study11p0 as S  # noqa: E402
from lifecycle11p0 import write_new  # noqa: E402
from strict import jbytes  # noqa: E402


def analyze(study, run_dir, out):
    pairs, prov = S.admit(study, run_dir)
    write_new(out, jbytes({"provenance": prov, **A10.analyze(pairs)}))


if __name__ == "__main__":
    analyze(S.Study(sys.argv[1], sys.argv[2]), sys.argv[3], sys.argv[4])
