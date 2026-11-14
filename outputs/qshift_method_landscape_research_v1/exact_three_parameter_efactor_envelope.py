"""Continuous exact-circuit gate/measurement/burst envelope for mean X.

Builds the scalar pair-cofire expectation as a separable rational polynomial
from the existing categorical fault-support map, then bounds it with tensor
Bernstein coefficients on three-parameter rectangles. No sampling occurs.
"""
from __future__ import annotations

import json
import hashlib
import math
import sys
import time
from fractions import Fraction
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for directory in (ROOT, ROOT / "outputs" / "phase3a_correlated_noise_preflight", ROOT / "outputs" / "stage4_noise_adaptive_feasibility_v1"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import categorical_circuit_feature_expectations as features
import cofire_category_continuous_envelope as logtools
from simulator import build_spatial_burst_circuit

PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))
DIMS = ("burst_p", "measurement_p", "gate_p")


def fraction_record(x: Fraction, compact: bool = False):
    if not compact:
        return {"numerator":str(x.numerator),"denominator":str(x.denominator),"float":float(x)}
    nbytes=x.numerator.to_bytes(max(1,(abs(x.numerator).bit_length()+8)//8),"big",signed=True)
    dbytes=x.denominator.to_bytes(max(1,(x.denominator.bit_length()+7)//8),"big")
    with localcontext() as ctx:
        ctx.prec=40
        approximate=format(Decimal(x.numerator)/Decimal(x.denominator),'.35g')
    return {"sign":0 if x==0 else (1 if x>0 else -1),"numerator_bits":abs(x.numerator).bit_length(),"denominator_bits":x.denominator.bit_length(),"canonical_fraction_sha256":hashlib.sha256(nbytes+b"/"+dbytes).hexdigest().upper(),"decimal_35_digits":approximate}


def circuit(params: tuple[float, float, float]):
    pb, pm, pg = params
    return build_spatial_burst_circuit(memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=pg, measurement_p=pm, bias_ratio=10.0, burst_probability=pb, burst_pair=(8, 10))


def multiply(a: list[Fraction], b: list[Fraction]) -> list[Fraction]:
    out = [Fraction(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    while len(out) > 1 and out[-1] == 0:
        out.pop()
    return out


def power_to_bernstein(poly: list[Fraction], lo: Fraction, hi: Fraction) -> list[Fraction]:
    n = len(poly) - 1
    width = hi - lo
    power_t = [sum((poly[j] * math.comb(j, k) * lo ** (j-k) * width ** k for j in range(k, n+1)), Fraction(0)) for k in range(n+1)]
    return [sum((power_t[k] * Fraction(math.comb(i,k), math.comb(n,k)) for k in range(i+1)), Fraction(0)) for i in range(n+1)]


def elevate(values: list[Fraction], degree: int) -> list[Fraction]:
    n = len(values) - 1
    if degree < n:
        raise ValueError("degree elevation cannot lower degree")
    return [sum((values[j] * Fraction(math.comb(n,j) * math.comb(degree-n,i-j), math.comb(degree,i))
                 for j in range(max(0, i-(degree-n)), min(n,i)+1)), Fraction(0)) for i in range(degree+1)]


def endpoint_templates(nominal_mapped, nominal_names):
    # Endpoint raw templates let the source's changing probabilities be checked
    # against the ideal rational channel law while supports stay fixed.
    endpoints = {
        "burst_p": (0.0005, 0.0015),
        "measurement_p": (0.001, 0.005),
        "gate_p": (0.002, 0.004),
    }
    templates = {}
    for dim, (x0, x1) in endpoints.items():
        for x in (x0, x1):
            params = [0.010, 0.003, 0.003]
            params[DIMS.index(dim)] = x
            c = circuit(tuple(params))
            names = [inst.name for inst in c]
            raw = features.extract_sites(c)
            if names != nominal_names or len(raw) != len(nominal_mapped):
                raise RuntimeError(f"circuit/site structure changed while varying {dim}")
            templates[(dim, x)] = raw
    return endpoints, templates


def build_character_polynomials(nominal_circuit, mapped_sites):
    names = [inst.name for inst in nominal_circuit]
    endpoints, templates = endpoint_templates(mapped_sites, names)
    # Map each raw channel alternative to the deterministic detector support from the nominal circuit.
    support_maps = []
    nominal_raw = features.extract_sites(nominal_circuit)
    for raw, mapped in zip(nominal_raw, mapped_sites):
        by_pauli = {paulis: (support, obs, paulis) for _, support, obs, paulis in mapped[1]}
        alts = []
        for probability, paulis in raw[2]:
            if paulis not in by_pauli:
                raise RuntimeError("nominal mapping omitted a nonzero raw alternative")
            alts.append(by_pauli[paulis])
        support_maps.append(alts)

    # Verify the source's balanced-channel probability allocation at endpoints,
    # midpoints, and quarter points. The exact polynomial below uses the intended
    # rational law: pg/3, pg/15, pm, and pb.
    max_probability_roundoff = 0.0
    for dim, (x0, x1) in endpoints.items():
        probes=(x0,x0+(x1-x0)/4,(x0+x1)/2,x0+3*(x1-x0)/4,x1)
        for x in probes:
            params=[.010,.003,.003]; params[DIMS.index(dim)]=x
            raw_probe=features.extract_sites(circuit(tuple(params)))
            if len(raw_probe)!=len(nominal_raw):
                raise RuntimeError(f"site count changed at {dim}={x}")
            for site_i,(rnom,rprobe) in enumerate(zip(nominal_raw,raw_probe)):
                channel=names[rnom[0]]
                channel_dim="burst_p" if channel=="E" else "measurement_p" if channel in ("X_ERROR","Z_ERROR") else "gate_p" if channel.startswith("PAULI_CHANNEL") else None
                if channel_dim!=dim:
                    continue
                if len(rprobe[2])!=len(support_maps[site_i]):
                    raise RuntimeError(f"alternative count changed in site {site_i} for {dim}")
                coefficient=(1.0/3.0 if channel=="PAULI_CHANNEL_1" else 1.0/15.0 if channel=="PAULI_CHANNEL_2" else 1.0)
                for alt_i,((probability,paulis),(_support,_obs,mapped_paulis)) in enumerate(zip(rprobe[2],support_maps[site_i])):
                    if paulis!=mapped_paulis:
                        raise RuntimeError("Pauli alternative ordering changed")
                    error=abs(probability-x*coefficient)
                    max_probability_roundoff=max(max_probability_roundoff,error)
                    if error>2e-14:
                        raise RuntimeError(f"Stim probability differs from ideal rational allocation by {error}")

    chars = {}
    supports = sorted({(a,) for pair in PAIRS for a in pair} | {tuple(pair) for pair in PAIRS})
    for selected in supports:
        polynomials = {d: [Fraction(1)] for d in DIMS}
        for site_i, raw in enumerate(nominal_raw):
            channel = names[raw[0]]
            if channel=="PAULI_CHANNEL_1": dim,denom="gate_p",3
            elif channel=="PAULI_CHANNEL_2": dim,denom="gate_p",15
            elif channel in ("X_ERROR","Z_ERROR"): dim,denom="measurement_p",1
            elif channel=="E": dim,denom="burst_p",1
            else: continue
            odd=sum(1 for support,_obs,_paulis in support_maps[site_i]
                    if len(set(selected).intersection(support))%2)
            polynomials[dim]=multiply(polynomials[dim],[Fraction(1),Fraction(-2*odd,denom)])
        chars[selected] = polynomials
    return chars, endpoints, support_maps, nominal_raw, names, max_probability_roundoff


def tensor_bernstein(chars, box):
    maxdeg = [max(len(chars[s][d])-1 for s in chars) for d in DIMS]
    degree_vectors = []
    for selected in chars:
        vectors = []
        for d, degree in zip(DIMS, maxdeg):
            lo, hi = box[d]
            vectors.append(elevate(power_to_bernstein(chars[selected][d], lo, hi), degree))
        degree_vectors.append((selected, vectors))
    shape = tuple(x+1 for x in maxdeg)
    tensor = np.empty(shape, dtype=object)
    for idx in np.ndindex(shape): tensor[idx] = Fraction(0)
    tensor.fill(Fraction(0))
    for a, b in PAIRS:
        for selected, sign in (((a,), -1), ((b,), -1), ((a,b), 1)):
            vectors = dict(degree_vectors)[selected]
            for idx in np.ndindex(shape):
                tensor[idx] += Fraction(sign, 20) * vectors[0][idx[0]] * vectors[1][idx[1]] * vectors[2][idx[2]]
    for idx in np.ndindex(shape): tensor[idx] += Fraction(5,20)
    values = [x for x in tensor.flat]
    return {"degree": maxdeg, "min": min(values), "max": max(values), "coefficient_count": len(values)}


def eval_poly(poly, x: Fraction) -> Fraction:
    value = Fraction(0)
    for coefficient in reversed(poly):
        value = value*x + coefficient
    return value


def eval_x(chars, params):
    pb, pm, pg = params
    values = {d: Fraction(0) for d in DIMS}
    for d, x in zip(DIMS, params):
        values[d] = Fraction.from_float(float(x))
    out = Fraction(0)
    for a,b in PAIRS:
        chi = lambda s: math.prod(eval_poly(chars[s][d], values[d]) for d in DIMS)
        out += 1 - chi((a,)) - chi((b,)) + chi((a,b))
    return out / 20


def direct_x_mean(params, support_maps, nominal_names):
    c = circuit(tuple(map(float, params)))
    names = [inst.name for inst in c]
    raw = features.extract_sites(c)
    if names != nominal_names or len(raw) != len(support_maps):
        raise RuntimeError("validation point changes the categorical site structure")
    sites=[]
    for site, alts in zip(raw, support_maps):
        mapped_alts=[]
        for (probability, paulis), (support, obs, mapped_paulis) in zip(site[2], alts):
            if paulis != mapped_paulis:
                raise RuntimeError("validation point changes Pauli ordering")
            mapped_alts.append((probability, support, obs, paulis))
        sites.append((site[1], mapped_alts))
    mean=features.means_from_characters(sites)
    return float(np.mean(mean[40:45]))


def chord_expected_log_lower(mean_null_upper: Fraction, mean_alt_lower: Fraction, lam: Fraction):
    """Concavity chord bound for X in [0,1], with rational log intervals."""
    factor_zero = 1 - lam
    factor_one = 1 + lam * (1 / mean_null_upper - 1)
    if factor_zero <= 0 or factor_one <= factor_zero:
        raise ValueError("invalid e-factor endpoints")
    log_zero = logtools.log_rational_interval(factor_zero, terms=24)
    log_one = logtools.log_rational_interval(factor_one, terms=24)
    lower = (1 - mean_alt_lower) * log_zero[1] + mean_alt_lower * log_one[0]
    return {"lambda": float(lam), "endpoint_factors": [float(factor_zero), float(factor_one)],
            "log_interval_zero": [float(log_zero[0]),float(log_zero[1])],
            "log_interval_one": [float(log_one[0]),float(log_one[1])],
            "exact_log_interval_zero": [fraction_record(log_zero[0],compact=True),fraction_record(log_zero[1],compact=True)],
            "exact_log_interval_one": [fraction_record(log_one[0],compact=True),fraction_record(log_one[1],compact=True)],
            "exact_uniform_expected_log_lower_bound":fraction_record(lower,compact=True),
            "uniform_expected_log_lower_bound_nats_per_shot": float(lower),
            "strictly_positive": lower > 0}


def chord_optimal_lambda(mean_null_upper: Fraction, mean_alt_lower: Fraction):
    # Exact maximizer of (1-m1)log(1-lambda)+m1 log(1+lambda*(1/m0-1)).
    a=1/mean_null_upper-1
    lam=mean_alt_lower-(1-mean_alt_lower)/a
    if not 0 < lam < 1:
        raise RuntimeError("endpoint-chord optimum lies outside (0,1)")
    row=chord_expected_log_lower(mean_null_upper,mean_alt_lower,lam)
    row["exact_optimal_lambda"]=fraction_record(lam)
    row["optimization_target"]="worst-case endpoint-chord expected-log lower bound; not realized delay"
    return row


def main():
    start = time.perf_counter()
    nominal = circuit((.010,.003,.003))
    mapped, metadata = features.categorical_sites(nominal)
    chars, _, support_maps, nominal_raw, names, max_probability_roundoff = build_character_polynomials(nominal, mapped)
    null_box = {"burst_p": (Fraction(0),Fraction(2,1000)), "measurement_p": (Fraction(1,1000),Fraction(5,1000)), "gate_p": (Fraction(2,1000),Fraction(4,1000))}
    high_box = {"burst_p": (Fraction(10,1000),Fraction(18,1000)), "measurement_p": (Fraction(1,1000),Fraction(5,1000)), "gate_p": (Fraction(2,1000),Fraction(4,1000))}
    null_bound, high_bound = tensor_bernstein(chars,null_box), tensor_bernstein(chars,high_box)
    up_null = null_bound["max"]
    up_alt = high_bound["min"]
    down_null = 1 - high_bound["min"]
    down_alt = 1 - null_bound["max"]
    robust_growth = []
    for lam in (Fraction(1,1000),Fraction(3,1000),Fraction(5,1000)):
        robust_growth.append({
            "lambda":float(lam),
            "upward":chord_expected_log_lower(up_null,up_alt,lam),
            "downward_on_complement":chord_expected_log_lower(down_null,down_alt,lam),
        })
    probes = [
        (.001,.001,.002),(.002,.005,.004),(.001,.003,.003),
        (.010,.001,.002),(.018,.005,.004),(.014,.003,.003),
        (.018,.001,.002),(.010,.005,.004),
    ]
    validations=[]
    for point in probes:
        polynomial=float(eval_x(chars, point))
        direct=direct_x_mean(point, support_maps, names)
        validations.append({"parameters":point,"polynomial_mean_X":polynomial,"exact_categorical_feature_mean_X":direct,"absolute_error":abs(polynomial-direct)})
    validation_max=max(v["absolute_error"] for v in validations)
    if validation_max > 2e-11:
        raise RuntimeError(f"tensor-polynomial construction validation failed: {validation_max}")
    result = {
        "classification": "EXACT_CATEGORICAL_CIRCUIT_CONTINUOUS_THREE_PARAMETER_BERNSTEIN_ENVELOPES",
        "feature": "X = mean of the five declared pair-cofire indicators",
        "ideal_rational_noise_law": {"balanced_one_qubit_alternative_probability":"gate_p/3","balanced_two_qubit_alternative_probability":"gate_p/15","measurement_flip_probability":"measurement_p","each_correlated_burst_probability":"burst_p","source":"outputs/phase2b_pauli_bias/noise_model.py; independent per-site categorical mechanisms"},
        "stim_float_probe_check_max_abs_probability_difference":max_probability_roundoff,
        "null_rectangle": {k:[float(v[0]),float(v[1])] for k,v in null_box.items()},
        "high_alternative_rectangle": {k:[float(v[0]),float(v[1])] for k,v in high_box.items()},
        "parameter_intervals_exact": {"null":{k:[fraction_record(v[0]),fraction_record(v[1])] for k,v in null_box.items()},"high_alternative":{k:[fraction_record(v[0]),fraction_record(v[1])] for k,v in high_box.items()}},
        "tensor_bernstein": {
            "null_box": {"degrees":null_bound["degree"],"coefficient_count":null_bound["coefficient_count"],"exact_mean_lower_bound":fraction_record(null_bound["min"]),"exact_mean_upper_bound":fraction_record(null_bound["max"]),"mean_lower_bound":float(null_bound["min"]),"mean_upper_bound":float(null_bound["max"])},
            "high_box": {"degrees":high_bound["degree"],"coefficient_count":high_bound["coefficient_count"],"exact_mean_lower_bound":fraction_record(high_bound["min"]),"exact_mean_upper_bound":fraction_record(high_bound["max"]),"mean_lower_bound":float(high_bound["min"]),"mean_upper_bound":float(high_bound["max"])},
            "separation_certified_by_global_coefficient_ranges": high_bound["min"] > null_bound["max"],
            "exact_conservative_gap_lower_bound":fraction_record(high_bound["min"]-null_bound["max"]),
            "conservative_gap_lower_bound":float(high_bound["min"]-null_bound["max"]),
        },
        "robust_mean_e_factor_population_analysis": {
            "upward": {"exact_null_mean_upper":fraction_record(up_null),"exact_alternative_mean_lower":fraction_record(up_alt),"null_mean_upper":float(up_null),"alternative_mean_lower":float(up_alt)},
            "downward_on_complement_1_minus_X": {"exact_null_mean_upper":fraction_record(down_null),"exact_alternative_mean_lower":fraction_record(down_alt),"null_mean_upper":float(down_null),"alternative_mean_lower":float(down_alt)},
            "log_growth_method":"For Z in [0,1], log(1+lambda*(Z/m0-1)) is concave and lies above its endpoint chord. The expected chord increases with E[Z]; use continuous Bernstein m0 upper and alternative-mean lower, and rational atanh log intervals.",
            "lambda_candidates":robust_growth,
            "endpoint_chord_optimum":{
                "upward":chord_optimal_lambda(up_null,up_alt),
                "downward_on_complement":chord_optimal_lambda(down_null,down_alt),
            },
            "scope":"Population e-factor validity and positive alternative expected-log lower bounds for fixed per-shot parameter rectangles; not an implemented detector, alarm, delay, or repeated-switch policy.",
        },
        "polynomial_vs_exact_feature_validation": {"probes":validations,"max_abs_error":validation_max},
        "mapping":metadata,
        "elapsed_wall_seconds":time.perf_counter()-start,
        "limitations":[
            "Circuit support map is deterministic and exact for the existing categorical fault model; per-site probabilities are required to be affine in their assigned physical parameter and are midpoint-checked.",
            "Tensor Bernstein coefficient extrema are valid continuous bounds, but global-degree coefficients may be loose; no subdivision is included in this first certificate.",
            "This bounds population means and supports a robust mean e-factor only if the supplied gate/measurement/burst rectangles are the actual null and alternative sets. It does not implement a sequential process or establish finite-horizon alarm performance.",
            "No detector histories, sampling, decoders, or protected data were accessed."
        ]
    }
    out=HERE/"EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json"
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(out),"elapsed":result["elapsed_wall_seconds"],"null":result["tensor_bernstein"]["null_box"],"high":result["tensor_bernstein"]["high_box"],"gap":result["tensor_bernstein"]["conservative_gap_lower_bound"]},indent=2))


if __name__=="__main__": main()
