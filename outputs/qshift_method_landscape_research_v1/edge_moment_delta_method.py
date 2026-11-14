"""IID asymptotic delta-method sensitivity for published burst-edge moments.

Uses exact categorical-circuit feature means/covariance only. It does not
generate finite detector histories and is not a finite-sample guarantee.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import numpy as np
import categorical_circuit_parameter_grid_audit as grid

HERE = Path(__file__).resolve().parent
PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))


def edge_p(x: np.ndarray) -> float:
    a, b, c = map(float, x)
    u = c - a*b
    v = 1 - 2*(a+b) + 4*c
    rad = .25 - u/v
    if rad <= 0 or v == 0:
        raise ValueError('edge inversion outside differentiable real domain')
    return .5 - np.sqrt(rad)


def edge_gradient(x: np.ndarray) -> np.ndarray:
    a, b, c = map(float, x)
    u = c-a*b
    v = 1-2*(a+b)+4*c
    rad = .25-u/v
    if rad <= 0 or v == 0:
        raise ValueError('edge inversion outside differentiable real domain')
    dr = np.array([(b*v-2*u)/v**2, (a*v-2*u)/v**2, (4*u-v)/v**2])
    return -dr/(2*np.sqrt(rad))


def edge_hessian(x: np.ndarray) -> np.ndarray:
    a,b,c=map(float,x); u=c-a*b; v=1-2*(a+b)+4*c
    gu=np.array([-b,-a,1.]); hu=np.array([[0.,-1.,0.],[-1.,0.,0.],[0.,0.,0.]])
    hv=np.array([-2.,-2.,4.])
    hw=hu/v-(np.outer(gu,hv)+np.outer(hv,gu))/v**2+2*u*np.outer(hv,hv)/v**3
    hr=-hw; gr=-(gu/v-u*hv/v**2); rad=.25-u/v
    return -hr/(2*np.sqrt(rad))+np.outer(gr,gr)/(4*rad**1.5)


def main() -> None:
    circuit = grid.construct(.010, .003)
    template, _ = grid.categorical_sites(circuit)
    def profile_summary(burst_p: float, meas_p: float, *, gradient_check: bool=False) -> dict:
        c=grid.construct(burst_p,meas_p)
        sites=grid.reweight(template,c)
        means=grid.means_from_characters(sites)
        covariance=grid.exact_cov(sites,means)
        gradients=[]; estimates=[]; fd_errors=[]; hessian_errors=[]; bias_coefficients=[]
        for k,(i,j) in enumerate(PAIRS):
            idx=np.array([i,j,40+k]); x=means[idx]; g=edge_gradient(x)
            gradients.append((idx,g)); estimates.append(edge_p(x))
            hess=edge_hessian(x)
            sigma_x=covariance[np.ix_(idx,idx)]
            bias_coefficients.append(float(.5*np.trace(hess@sigma_x)))
            if gradient_check:
                fd=np.empty(3)
                for col in range(3):
                    h=1e-7; plus=x.copy(); minus=x.copy(); plus[col]+=h; minus[col]-=h
                    fd[col]=(edge_p(plus)-edge_p(minus))/(2*h)
                fd_errors.append(float(np.max(np.abs(fd-g))))
                fd_hess=np.empty((3,3))
                for col in range(3):
                    h=1e-6; plus=x.copy(); minus=x.copy(); plus[col]+=h; minus[col]-=h
                    fd_hess[:,col]=(edge_gradient(plus)-edge_gradient(minus))/(2*h)
                hessian_errors.append(float(np.max(np.abs(fd_hess-hess))))
        cov_edges=np.empty((5,5))
        for a,(idx_a,g_a) in enumerate(gradients):
            for b,(idx_b,g_b) in enumerate(gradients):
                cov_edges[a,b]=g_a@covariance[np.ix_(idx_a,idx_b)]@g_b
        ones=np.ones(5)/5
        coefficient=float(np.sqrt(ones@cov_edges@ones))
        bias_coefficient=float(np.mean(bias_coefficients))
        neg_prob={}; clip_bias={}
        for n in (200,500,1000,2000):
            sd=coefficient/np.sqrt(n); z=burst_p/sd
            neg_prob[str(n)]=float(.5*math.erfc(z/np.sqrt(2)))
            phi=float(np.exp(-.5*z*z)/np.sqrt(2*np.pi))
            clip_bias[str(n)]=float(sd*phi-burst_p*neg_prob[str(n)])
        return {'burst_p':burst_p,'measurement_p':meas_p,
                'equal_average_population_estimate':float(ones@estimates),
                'equal_average_asymptotic_sd_coefficient_per_sqrt_shots':coefficient,
                'equal_average_second_order_bias_coefficient_over_N':bias_coefficient,
                'equal_average_asymptotic_second_order_bias_at_N':{str(n):bias_coefficient/n for n in (200,500,1000,2000)},
                'normal_approx_probability_raw_estimate_below_zero':neg_prob,
                'normal_approx_bias_if_clipped_at_zero':clip_bias,
                'shots_for_three_asymptotic_standard_errors_from_zero':float((3*coefficient/burst_p)**2),
                'individual_edge_sd_coefficients_per_sqrt_shots':np.sqrt(np.diag(cov_edges)).tolist(),
                **({'analytic_gradient_central_difference_max_abs_error':max(fd_errors),
                    'analytic_hessian_gradient_difference_max_abs_error':max(hessian_errors)} if fd_errors else {})}
    nominal=profile_summary(.010,.003,gradient_check=True)
    sensitivity=[profile_summary(b,m) for b in (.002,.010,.018) for m in (.001,.003,.005)]
    result = {
        'classification': 'IID_ASYMPTOTIC_DELTA_METHOD_NOT_FINITE_SAMPLE_VALIDATION',
        'configuration': {'burst_p': .010, 'measurement_p': .003, 'gate_p': .003,
                          'distance': 3, 'rounds': 5, 'features': 'exact categorical circuit'},
        'nominal_profile': nominal,
        'deterministic_population_sensitivity_grid': sensitivity,
        'comparability_note': 'These are iid delta-method asymptotics conditional on the exact model and known feature covariance. Second-order bias uses the raw sample means of each detector bit and pair cofire with analytic Hessians. Negative-estimate probability and bias after clipping at zero are unbounded-normal approximations, not exact finite-sample probabilities. The shots-for-three-SE values are scale heuristics against zero, not power or a design recommendation. Overlapping windows, temporal dependence, fitted nuisance parameters, and edge-model misspecification are not included.',
        'sampling_calls': 0, 'decoder_calls': 0,
    }
    out=HERE/'EDGE_MOMENT_DELTA_METHOD.json'
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'output':out.name,'nominal':nominal,'sensitivity_count':len(sensitivity),
                      'max_gradient_check':nominal['analytic_gradient_central_difference_max_abs_error']},indent=2))


if __name__=='__main__':
    main()
