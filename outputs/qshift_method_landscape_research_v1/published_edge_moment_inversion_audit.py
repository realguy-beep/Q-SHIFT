"""Deterministically apply the published independent-edge moment inversion.

This asks whether the syndrome-pair inversion from Bhardwaj et al. tracks the
known Q-SHIFT burst-edge rates at the population-feature level. It evaluates
exact categorical-circuit moments and approximate-DEM moments separately.
No sampled syndromes, decoder, logical labels, or performance outcomes are used.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
import categorical_circuit_parameter_grid_audit as grid

BURST_PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))


def invert_edge_probability(mean_i: float, mean_j: float, pair_mean: float) -> dict:
    """Equation (1) in Bhardwaj et al. for an independent edge graph model."""
    covariance = pair_mean - mean_i * mean_j
    denominator = 1 - 2 * (mean_i + mean_j) + 4 * pair_mean
    radicand = 0.25 - covariance / denominator if denominator != 0 else float('nan')
    if not np.isfinite(radicand) or radicand < -1e-12:
        return {'estimate': None, 'covariance': covariance, 'denominator': denominator,
                'radicand': radicand, 'status': 'invalid_real_domain'}
    radicand = max(0.0, radicand)
    return {'estimate': float(0.5 - np.sqrt(radicand)), 'covariance': covariance,
            'denominator': denominator, 'radicand': radicand, 'status': 'ok'}


def main() -> None:
    base = grid.construct(.010, .003)
    template, _ = grid.categorical_sites(base)
    signature = grid.circuit_signature(base)
    exact, dem, direct_error = grid.run_grid(template, signature)
    rows = []
    for (burst_p, measurement_p), means in sorted(exact.items()):
        dem_means = dem[(burst_p, measurement_p)]
        for k, (i, j) in enumerate(BURST_PAIRS):
            exact_fit = invert_edge_probability(float(means[i]), float(means[j]), float(means[40+k]))
            dem_fit = invert_edge_probability(float(dem_means[i]), float(dem_means[j]), float(dem_means[40+k]))
            rows.append({
                'burst_p': burst_p, 'measurement_p': measurement_p,
                'pair': [i, j], 'exact_categorical_circuit': exact_fit,
                'approximate_dem': dem_fit,
                'true_burst_probability_for_model_comparison_only': burst_p,
            })
    valid = [r for r in rows if r['exact_categorical_circuit']['estimate'] is not None]
    errors = [abs(r['exact_categorical_circuit']['estimate'] - r['burst_p']) for r in valid]
    dem_valid = [r for r in rows if r['approximate_dem']['estimate'] is not None]
    dem_errors = [abs(r['approximate_dem']['estimate'] - r['burst_p']) for r in dem_valid]
    gate_rows = []
    for gate_p in (.002, .003, .004):
        for burst_p in (.002, .010, .018):
            circuit = grid.build_spatial_burst_circuit(
                memory_basis='z', regime='balanced', distance=3, rounds=5,
                gate_p=gate_p, measurement_p=.003, bias_ratio=10.,
                burst_probability=burst_p, burst_pair=(8, 10))
            if grid.circuit_signature(circuit) != signature:
                raise RuntimeError('gate-rate sensitivity changed non-noise circuit structure')
            means = grid.means_from_characters(grid.reweight(template, circuit))
            estimates = [invert_edge_probability(float(means[i]), float(means[j]), float(means[40+k]))
                         for k, (i, j) in enumerate(BURST_PAIRS)]
            gate_rows.append({'gate_p': gate_p, 'measurement_p': .003, 'burst_p': burst_p,
                              'pair_estimates': estimates})
    gate_errors = [abs(x['estimate']-r['burst_p']) for r in gate_rows
                   for x in r['pair_estimates'] if x['estimate'] is not None]
    regime_rows=[]; regime_direct_error=0.0
    for regime in ('x_biased','z_biased'):
        for burst_p in (.002,.010,.018):
            circuit=grid.build_spatial_burst_circuit(
                memory_basis='z', regime=regime, distance=3, rounds=5,
                gate_p=.003, measurement_p=.003, bias_ratio=10.,
                burst_probability=burst_p, burst_pair=(8,10))
            if grid.circuit_signature(circuit)!=signature:
                raise RuntimeError('regime sensitivity changed non-noise circuit structure')
            sites=grid.reweight(template,circuit)
            means=grid.means_from_characters(sites)
            direct=grid.means_by_direct_xor(sites)
            regime_direct_error=max(regime_direct_error,float(np.max(np.abs(means-direct))))
            estimates=[invert_edge_probability(float(means[i]),float(means[j]),float(means[40+k]))
                       for k,(i,j) in enumerate(BURST_PAIRS)]
            regime_rows.append({'regime':regime,'gate_p':.003,'measurement_p':.003,
                                'burst_p':burst_p,'pair_estimates':estimates})
    regime_errors=[abs(x['estimate']-r['burst_p']) for r in regime_rows
                   for x in r['pair_estimates'] if x['estimate'] is not None]
    result = {
        'classification': 'DETERMINISTIC_POPULATION_APPLY_PUBLISHED_INDEPENDENT_EDGE_MOMENT_INVERSION',
        'source': {'citation': 'Bhardwaj et al., Adaptive Estimation of Drifting Noise in Quantum Error Correction, PRX Quantum 7, 033024 (2026), Eq. (1)',
                   'doi': '10.1103/z1hc-nqw5', 'url': 'https://doi.org/10.1103/z1hc-nqw5'},
        'configuration': {'distance': 3, 'rounds': 5, 'gate_p': .003, 'bias_ratio': 10,
                          'burst_pair': [8, 10], 'measurement_range': [.001, .005],
                          'burst_range': [.002, .018], 'grid_count': 81},
        'equation': 'p_ij = 1/2 - sqrt(1/4 - (E[Di Dj]-E[Di]E[Dj])/(1-2(E[Di]+E[Dj])+4E[Di Dj]))',
        'assumption': 'The inversion assumes independent graph-edge event mechanisms with boundary-edge contributions; it is not asserted to be exact for the categorical circuit or its approximate DEM.',
        'rows': rows,
        'exact_circuit_scalar_gate_mismatch_sensitivity': gate_rows,
        'exact_circuit_gate_composition_sensitivity': regime_rows,
        'summary': {
            'pair_estimates': len(rows),
            'exact_circuit_valid_count': len(valid),
            'exact_circuit_invalid_count': len(rows)-len(valid),
            'exact_circuit_mean_abs_error_vs_burst_p': float(np.mean(errors)) if errors else None,
            'exact_circuit_max_abs_error_vs_burst_p': float(max(errors)) if errors else None,
            'approximate_dem_valid_count': len(dem_valid),
            'approximate_dem_invalid_count': len(rows)-len(dem_valid),
            'approximate_dem_mean_abs_error_vs_burst_p': float(np.mean(dem_errors)) if dem_errors else None,
            'approximate_dem_max_abs_error_vs_burst_p': float(max(dem_errors)) if dem_errors else None,
            'gate_mismatch_pair_estimate_count': len(gate_errors),
            'gate_mismatch_max_abs_error_vs_burst_p': float(max(gate_errors)) if gate_errors else None,
            'gate_composition_pair_estimate_count': len(regime_errors),
            'gate_composition_max_abs_error_vs_burst_p': float(max(regime_errors)) if regime_errors else None,
            'gate_composition_max_direct_xor_validation_error': regime_direct_error,
            'max_parity_identity_vs_direct_xor_error': float(direct_error),
        },
        'interpretation_limits': [
            'Population expectations only; no finite-history variance, online alarm operating characteristics, or estimation delay is assessed.',
            'Circuit and DEM results remain distinct. DEM-level validity does not prove original-circuit validity.',
            'A disagreement with burst p can arise because the inversion estimates an effective independent-edge parameter, not necessarily the physical burst probability.',
            'No decoder, logical outcome, sampling, training, or protected data is used.',
        ],
        'sampling_calls': 0, 'decoder_calls': 0,
    }
    path = HERE / 'PUBLISHED_EDGE_MOMENT_INVERSION_AUDIT.json'
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'output': path.name, 'summary': result['summary']}, indent=2))


if __name__ == '__main__':
    main()
