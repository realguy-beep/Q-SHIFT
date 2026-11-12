"""Generate versioned population templates by deterministic model algebra.

This script never calls a Stim sampler. Exact-categorical and approximate DEM
families are generated and serialized separately.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import stim

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from outputs.qshift_advanced_decoder_research_v2b import analyze_identifiability as b2
from outputs.qshift_advanced_decoder_research_v2c import joint_estimator_comparison as c2
from outputs.qshift_advanced_research_v3a.qshift_estimators import TemplateBank

OUT=Path(__file__).resolve().parent/'template_bank_v1.json'


def main() -> None:
    ref=build_spatial_burst_circuit(gate_p=.003,measurement_p=.003,burst_probability=.008)
    physical,mapping=b2.extract_physical_signatures(ref)
    exact=c2.make_template_table('circuit',physical)
    dem=c2.make_template_table('dem',physical)
    provenance={
        'generated_from_reviewed_commit':'abcafd6f36023ae5016ccf2e7c69a674e608351d',
        'stim_version':stim.__version__,
        'circuit':{'memory_basis':'z','regime':'balanced','distance':3,'rounds':5,
                   'gate_p':.003,'measurement_base_p':.003,'burst_mechanism':'independent CORRELATED_ERROR(p) X8 X10 at five MR boundaries'},
        'burst_probability_range':[0.0,.020],
        'measurement_probability_range':[0.0,.010],
        'burst_template_step':.001,'measurement_template_step':.001,
        'candidate_b_fit_step':.0001,
        'candidate_a_profile_knots':[0.0,.005,.010,.015,.020],
        'candidate_a_fit_step':.00001,
        'gate_p':.003,
        'feature_pairs':[list(p) for p in b2.BURST_DETECTOR_PAIRS],
        'exact_categorical_model':'independent fault locations; mutually exclusive PAULI_CHANNEL alternatives; exact single-fault detector masks plus parity-character expectations',
        'approximate_dem_model':{'decompose_errors':True,'approximate_disjoint_errors':True,
                                 'interpretation':'exact expectation under the emitted independent-mechanism DEM approximation'},
        'fault_mapping':mapping,
        'sampling':'none; deterministic construction and algebra only'}
    bank=TemplateBank.from_tables(exact,dem,provenance)
    digest=bank.save(OUT)
    check=TemplateBank.load(OUT)
    if not np.array_equal(check.means['exact_categorical'],exact):
        raise RuntimeError('serialized exact template bank failed round-trip')
    if not np.array_equal(check.means['approximate_dem'],dem):
        raise RuntimeError('serialized DEM template bank failed round-trip')
    print({'template_file':OUT.as_posix(),'sha256':digest,'shape':list(exact.shape),
           'stim_version':stim.__version__,'burst_masks':mapping['burst_masks']})


if __name__=='__main__':
    main()
