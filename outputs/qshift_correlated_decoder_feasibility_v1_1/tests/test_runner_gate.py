from __future__ import annotations

import sys
import unittest
from unittest import mock

from outputs.qshift_correlated_decoder_feasibility_v1_1 import run_eval


class RunnerGateTests(unittest.TestCase):
    def test_default_command_selects_sampler_free_dry_run(self) -> None:
        with mock.patch.object(sys, "argv", ["run_eval.py"]), \
             mock.patch.object(run_eval, "dry_run") as dry_run, \
             mock.patch.object(run_eval, "execute") as execute:
            run_eval.main()
        dry_run.assert_called_once()
        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
