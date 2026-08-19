"""Published spatial-temporal ETAS kernels and closed-form integrals."""

from __future__ import annotations

import math

from scipy.special import exp1, gamma as gamma_function, gammaincc

from etas_challenge.parameters import ETASParameters


def magnitude_density(magnitude: float, m_ref: float, beta: float) -> float:
    if beta <= 0:
        raise ValueError("beta must be positive")
    if magnitude < m_ref:
        return 0.0
    return beta * math.exp(-beta * (magnitude - m_ref))


def productivity(
    magnitude: float, m_ref: float, parameters: ETASParameters
) -> float:
    return parameters.k0 * math.exp(parameters.a * (magnitude - m_ref))


def temporal_kernel(delta_t: float, parameters: ETASParameters) -> float:
    if delta_t <= 0:
        return 0.0
    return math.exp(-delta_t / parameters.tau) / (
        (delta_t + parameters.c) ** (1.0 + parameters.omega)
    )


def temporal_integral(
    start: float,
    end: float,
    parameters: ETASParameters,
) -> float:
    if start < 0 or end <= start:
        raise ValueError("temporal bounds must satisfy 0 <= start < end")

    lower = (start + parameters.c) / parameters.tau
    upper = (end + parameters.c) / parameters.tau
    scale = math.exp(parameters.c / parameters.tau)

    if parameters.omega == 0:
        upper_value = 0.0 if math.isinf(end) else float(exp1(upper))
        return scale * (float(exp1(lower)) - upper_value)

    shape = -parameters.omega
    scale *= parameters.tau ** (-parameters.omega)
    lower_value = _upper_incomplete_gamma(shape, lower)
    upper_value = 0.0 if math.isinf(end) else _upper_incomplete_gamma(shape, upper)
    return scale * (lower_value - upper_value)


def spatial_scale(
    magnitude: float, m_ref: float, parameters: ETASParameters
) -> float:
    return parameters.d * math.exp(parameters.gamma * (magnitude - m_ref))


def spatial_kernel(
    delta_x: float,
    delta_y: float,
    magnitude: float,
    m_ref: float,
    parameters: ETASParameters,
) -> float:
    scale = spatial_scale(magnitude, m_ref, parameters)
    radius_squared = delta_x * delta_x + delta_y * delta_y
    return (radius_squared + scale) ** (-(1.0 + parameters.rho))


def spatial_integral_disk(
    radius: float,
    magnitude: float,
    m_ref: float,
    parameters: ETASParameters,
) -> float:
    if radius <= 0 and not math.isinf(radius):
        raise ValueError("radius must be positive")
    scale = spatial_scale(magnitude, m_ref, parameters)
    tail = 0.0 if math.isinf(radius) else (radius * radius + scale) ** (-parameters.rho)
    return math.pi / parameters.rho * (scale ** (-parameters.rho) - tail)


def triggering_rate(
    magnitude: float,
    delta_t: float,
    delta_x: float,
    delta_y: float,
    m_ref: float,
    parameters: ETASParameters,
) -> float:
    if delta_t <= 0:
        return 0.0
    return (
        productivity(magnitude, m_ref, parameters)
        * temporal_kernel(delta_t, parameters)
        * spatial_kernel(delta_x, delta_y, magnitude, m_ref, parameters)
    )


def expected_direct_aftershocks(
    magnitude: float, m_ref: float, parameters: ETASParameters
) -> float:
    magnitude_delta = magnitude - m_ref
    space_time_integral = (
        temporal_integral(0.0, math.inf, parameters)
        * math.pi
        * parameters.d ** (-parameters.rho)
        / parameters.rho
    )
    return (
        parameters.k0
        * math.exp(parameters.productivity_exponent * magnitude_delta)
        * space_time_integral
    )


def branching_ratio(beta: float, parameters: ETASParameters) -> float:
    alpha = parameters.productivity_exponent
    if beta <= alpha:
        raise ValueError("branching ratio is finite only when beta > a - rho*gamma")
    temporal = temporal_integral(0.0, math.inf, parameters)
    return (
        beta
        * parameters.k0
        * math.pi
        * parameters.d ** (-parameters.rho)
        * temporal
        / (parameters.rho * (beta - alpha))
    )


def _upper_incomplete_gamma(shape: float, value: float) -> float:
    return float(gammaincc(shape, value) * gamma_function(shape))
