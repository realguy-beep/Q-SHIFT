"""E1T: E1 with a threshold-free flag (PLAN_BRT.md). estimate3 (BRE) and estimate4 (BRS) are imported, not modified.

  e1t_flag(e1_fit, structural)   flagged iff E1 excluded more than E1_MAX_EXCLUDED detectors (larger than any burst
                                 class; a code property) OR the subset-rule shape (S1) OR consistency (S2) check fails.
No residual statistic, no tuned parameter.
"""
from __future__ import annotations

import brt_config as C


def e1t_flag(e1_fit, structural):
    return bool(e1_fit["excluded"] > C.E1_MAX_EXCLUDED or structural["S1_shape"] or structural["S2_consistency"])
