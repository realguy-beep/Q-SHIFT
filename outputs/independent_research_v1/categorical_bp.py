"""Loopy sum-product screening decoder for categorical Pauli fault locations.

Each location remains a mutually exclusive categorical variable. Binary parity
checks enforce the observed detector and hypothesized logical bits. The ratio of
Bethe partition estimates for logical 0 and 1 is approximate on loopy graphs.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, log

from categorical_reference import CategoricalModel


@dataclass(frozen=True)
class DecodeResult:
    logical_one_probability: float
    iterations: int
    converged: bool


def _normalise(values):
    total = sum(values)
    if total <= 0:
        return [1.0 / len(values)] * len(values)
    return [value / total for value in values]


def _log_bethe_partition(priors, effects, neighbors, variable_checks,
                         var_to_check, check_to_var, targets):
    log_z = 0.0
    for check, variables in enumerate(neighbors):
        parity_bias = 1.0
        for variable in variables:
            message = var_to_check[variable, check]
            p_even = sum(message[k] for k, bit in enumerate(effects[variable][check]) if bit == 0)
            parity_bias *= 2.0 * p_even - 1.0
        z_factor = (1.0 + (1.0 if targets[check] == 0 else -1.0) * parity_bias) / 2.0
        if z_factor <= 0:
            return float("-inf")
        log_z += log(z_factor)

    for variable, checks in enumerate(variable_checks):
        z_variable = 0.0
        for outcome, prior in enumerate(priors[variable]):
            value = prior
            for check in checks:
                value *= check_to_var[check, variable][effects[variable][check][outcome]]
            z_variable += value
        if z_variable <= 0:
            return float("-inf")
        log_z += log(z_variable)

        for check in checks:
            edge_z = sum(var_to_check[variable, check][outcome]
                         * check_to_var[check, variable][effects[variable][check][outcome]]
                         for outcome in range(len(priors[variable])))
            if edge_z <= 0:
                return float("-inf")
            log_z -= log(edge_z)
    return log_z


def _conditioned_log_partition(model, syndrome, logical_target, *,
                               max_iterations, damping, tolerance):
    priors = [[outcome.probability for outcome in location.outcomes]
              for location in model.locations]
    effects = []
    for location in model.locations:
        location_effects = [[(outcome.detector_mask >> detector) & 1
                             for outcome in location.outcomes]
                            for detector in range(model.detector_count)]
        location_effects.append([outcome.observable_mask & 1 for outcome in location.outcomes])
        effects.append(location_effects)

    targets = [(syndrome >> detector) & 1 for detector in range(model.detector_count)] + [logical_target]
    neighbors = [[variable for variable in range(len(model.locations))
                  if any(effects[variable][check])]
                 for check in range(len(targets))]
    variable_checks = [[check for check in range(len(targets))
                        if any(effects[variable][check])]
                       for variable in range(len(model.locations))]
    var_to_check = {}
    check_to_var = {}
    for variable, checks in enumerate(variable_checks):
        for check in checks:
            var_to_check[variable, check] = priors[variable][:]
            check_to_var[check, variable] = [1.0, 1.0]

    converged = False
    for iteration in range(1, max_iterations + 1):
        updated_check = {}
        for check, variables in enumerate(neighbors):
            for variable in variables:
                other_parity_bias = 1.0
                for other in variables:
                    if other == variable:
                        continue
                    message = var_to_check[other, check]
                    p_even = sum(message[k] for k, bit in enumerate(effects[other][check]) if bit == 0)
                    other_parity_bias *= 2.0 * p_even - 1.0
                values = []
                for bit in effects[variable][check]:
                    sign = 1.0 if targets[check] ^ bit == 0 else -1.0
                    values.append(max(0.0, (1.0 + sign * other_parity_bias) / 2.0))
                updated_check[check, variable] = _normalise(values)

        updated_variable = {}
        largest_change = 0.0
        for variable, checks in enumerate(variable_checks):
            for check in checks:
                values = priors[variable][:]
                for other_check in checks:
                    if other_check == check:
                        continue
                    incoming = check_to_var[other_check, variable]
                    for outcome, bit in enumerate(effects[variable][other_check]):
                        values[outcome] *= incoming[bit]
                values = _normalise(values)
                old = var_to_check[variable, check]
                mixed = _normalise([(1.0 - damping) * old[k] + damping * values[k]
                                    for k in range(len(values))])
                largest_change = max(largest_change,
                                     max(abs(mixed[k] - old[k]) for k in range(len(old))))
                updated_variable[variable, check] = mixed
        var_to_check = updated_variable
        check_to_var = updated_check
        if largest_change < tolerance:
            converged = True
            break

    log_partition = _log_bethe_partition(priors, effects, neighbors, variable_checks,
                                         var_to_check, check_to_var, targets)
    return log_partition, iteration, converged


def logical_one_probability(model: CategoricalModel, syndrome: int, *,
                            max_iterations: int = 200, damping: float = 0.5,
                            tolerance: float = 1e-10) -> DecodeResult:
    """Approximate P(L=1 | syndrome) via two constrained Bethe partitions."""
    model.validate()
    if syndrome < 0 or syndrome >= (1 << model.detector_count):
        raise ValueError("syndrome is outside detector range")
    if not 0 < damping <= 1:
        raise ValueError("damping must be in (0, 1]")

    log_z = []
    iteration_counts = []
    convergence = []
    for logical_target in (0, 1):
        value, iterations, converged = _conditioned_log_partition(
            model, syndrome, logical_target, max_iterations=max_iterations,
            damping=damping, tolerance=tolerance)
        log_z.append(value)
        iteration_counts.append(iterations)
        convergence.append(converged)
    if log_z[0] == float("-inf") and log_z[1] == float("-inf"):
        return DecodeResult(0.5, max(iteration_counts), all(convergence))
    max_log_z = max(log_z)
    weights = [0.0 if value == float("-inf") else exp(value - max_log_z)
               for value in log_z]
    probability = weights[1] / sum(weights)
    return DecodeResult(probability, max(iteration_counts), all(convergence))
