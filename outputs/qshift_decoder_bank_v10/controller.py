"""CB with its memory stated explicitly (audit F6), and a selector that cannot return a rejected candidate (audit F9).

PROTOCOL_DB8 says CB uses "its own previous key", which has two readings. Frozen DB8 used LAST_BANK. There is no
default here: a future protocol must name one."""
from __future__ import annotations

LAST_BANK = "last_bank"          # last key chosen from a non-empty plausible set; kept through a W0F fallback
LAST_EMITTED = "last_emitted"    # the key actually used on the previous block, including a fallback's
MEMORIES = (LAST_BANK, LAST_EMITTED)


def cb_key(gf1, tau_fit, risk, prev, w0f_key, *, memory):
    """-> (key, source, next prev). `prev` is a bank state name, or None (LAST_EMITTED after a non-bank key)."""
    import db_core as D
    if memory not in MEMORIES:
        raise ValueError(f"memory {memory!r}")
    k, _ = D.bank_decide(gf1, 1, tau_fit, risk, prev)
    if k is not None:
        return "bank:" + k, "cb", k
    if memory == LAST_EMITTED:
        prev = w0f_key.split(":", 1)[1] if w0f_key.startswith("bank:") else None
    return w0f_key, "w0f", prev


class NoEligibleCandidate(ValueError):
    pass


def first_eligible(ranked, reject):
    """ranked labels in order; reject(label) -> reason or None. -> (label, [{"label", "reason"}]). Raises if none is left."""
    skipped = []
    for lab in ranked:
        why = reject(lab)
        if not why:
            return lab, skipped
        skipped.append({"label": lab, "reason": why})
    raise NoEligibleCandidate(f"no eligible candidate; skipped {skipped}")
