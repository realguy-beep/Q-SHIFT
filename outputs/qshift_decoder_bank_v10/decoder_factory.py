"""Separate decoder backends and a pre-freeze build check (audit F1).

re1.decoders builds BP+OSD and correlated matching together, although DB8 scores every bank key with BP+OSD only. An
unbuildable matching model therefore stopped attempt 2. Here each backend has its own builder (same construction calls
as re1.decoders; tested), and preflight builds exactly the (backend, state) pairs the scored arms need.

Limit: AD/AD3/W0-family arms can also decode with keys learned during an episode. Those cannot be listed before a run,
so preflight covers every fixed key only. A learned key that does not build still stops a run fail-closed."""
from __future__ import annotations

L2, MATCHING, PLAIN = "l2", "matching", "plain"


def build_l2(spec_model, support):
    import learner_d5 as LD
    import re1
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD
    c = m.build_base_circuit(spec_model) if support is None else \
        m.build_candidate_circuit(spec_model, re1.R.L2_PRIOR, tuple(support))
    return LdpcBPOSD(c.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True), LD.L2)


def build_matching(spec_model, support):
    import re1
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    c = m.build_base_circuit(spec_model) if support is None else \
        m.build_candidate_circuit(spec_model, re1.R.ASTAR_Q_DEC, tuple(support))
    return m.build_matching(m.build_decomposed_dem(c))


def build_plain(spec_model, support):
    """A_nominal's burst-free matching decoder."""
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    if support is not None:
        raise ValueError("the plain backend is burst-free")
    return m.build_matching(m.build_decomposed_dem(m.build_base_circuit(spec_model)))


BUILDERS = {L2: build_l2, MATCHING: build_matching, PLAIN: build_plain}


def build(kind, spec_model, support):
    return BUILDERS[kind](spec_model, support)


def db8_required():
    """[(label, backend, spec, support)] for every fixed key DB8's scored arms decode with, ORACLE included."""
    import db8_config as C
    p0 = C.spec(gate_p=C.P0, measurement_p=C.P0)
    nom = C.spec(**C.NOMINAL)
    req = [("bank:" + s, L2, p0, C.support(s)) for s in C.STATES + ("E",) + tuple(C.NEW_UNKNOWN)]
    return req + [("nominal", L2, nom, None), ("A_nominal", PLAIN, nom, None)]


def preflight(required, builders=None):
    """Build everything; -> sorted [(label, backend, error)] (empty = pass). Reports all failures, not only the first."""
    b = builders or BUILDERS
    bad = []
    for label, kind, spec_model, sup in required:
        try:
            b[kind](spec_model, sup)
        except Exception as ex:      # noqa: BLE001  (every construction failure is a finding)
            bad.append((label, kind, repr(ex)))
    return sorted(bad)
