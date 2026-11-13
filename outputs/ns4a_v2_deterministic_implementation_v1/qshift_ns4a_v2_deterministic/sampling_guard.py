"""Permanent prepare-only guard; no production sampling entry point exists."""

PRODUCTION_SAMPLING_ENABLED = False


class SamplingNotAuthorized(RuntimeError):
    """Raised if code attempts to activate an unimplemented scientific run."""


def activate_sampling(*_args, **_kwargs):
    raise SamplingNotAuthorized(
        "NS-4A V2 scientific sampling is unimplemented and unauthorized; this package is deterministic-only."
    )
