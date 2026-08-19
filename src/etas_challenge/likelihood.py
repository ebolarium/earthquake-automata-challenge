"""Event-level spatial-temporal ETAS likelihood components."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from etas_challenge.kernels import (
    productivity,
    spatial_integral_disk,
    temporal_integral,
    temporal_kernel,
    triggering_rate,
)
from etas_challenge.parameters import ETASParameters


@dataclass(frozen=True, slots=True)
class CatalogEvent:
    event_id: str
    time: float
    latitude: float
    longitude: float
    magnitude: float


@dataclass(frozen=True, slots=True)
class LikelihoodComponents:
    point_intensity: float
    temporal_intensity: float
    compensator: float

    @property
    def ll(self) -> float:
        return math.log(self.point_intensity) - self.compensator

    @property
    def tll(self) -> float:
        return math.log(self.temporal_intensity) - self.compensator

    @property
    def sll(self) -> float:
        return self.ll - self.tll


def haversine_distance(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
    earth_radius: float = 6_378.1,
) -> float:
    lat_a = math.radians(latitude_a)
    lat_b = math.radians(latitude_b)
    delta_lat = lat_a - lat_b
    delta_lon = math.radians(longitude_a - longitude_b)
    hav_lat = math.sin(delta_lat / 2.0) ** 2
    hav_lon = math.sin(delta_lon / 2.0) ** 2
    angle = 2.0 * math.asin(
        math.sqrt(hav_lat + math.cos(lat_a) * math.cos(lat_b) * hav_lon)
    )
    return earth_radius * angle


def point_intensity(
    target: CatalogEvent,
    history: Iterable[CatalogEvent],
    m_ref: float,
    parameters: ETASParameters,
    earth_radius: float = 6_378.1,
) -> float:
    value = parameters.mu
    for source in history:
        if source.time >= target.time:
            continue
        distance = haversine_distance(
            target.latitude,
            target.longitude,
            source.latitude,
            source.longitude,
            earth_radius,
        )
        value += triggering_rate(
            source.magnitude,
            target.time - source.time,
            distance,
            0.0,
            m_ref,
            parameters,
        )
    return value


def temporal_intensity(
    target_time: float,
    history: Iterable[CatalogEvent],
    area: float,
    m_ref: float,
    parameters: ETASParameters,
) -> float:
    value = parameters.mu * area
    for source in history:
        if source.time >= target_time:
            continue
        value += (
            productivity(source.magnitude, m_ref, parameters)
            * spatial_integral_disk(
                math.inf, source.magnitude, m_ref, parameters
            )
            * temporal_kernel(target_time - source.time, parameters)
        )
    return value


def interval_compensator(
    start: float,
    end: float,
    history: Iterable[CatalogEvent],
    area: float,
    m_ref: float,
    parameters: ETASParameters,
) -> float:
    if end <= start:
        raise ValueError("interval must satisfy start < end")
    value = parameters.mu * area * (end - start)
    for source in history:
        if source.time >= end:
            continue
        lower = max(0.0, start - source.time)
        upper = end - source.time
        if upper <= lower:
            continue
        value += (
            productivity(source.magnitude, m_ref, parameters)
            * spatial_integral_disk(
                math.inf, source.magnitude, m_ref, parameters
            )
            * temporal_integral(lower, upper, parameters)
        )
    return value


def likelihood_components(
    target: CatalogEvent,
    interval_start: float,
    history: Iterable[CatalogEvent],
    area: float,
    m_ref: float,
    parameters: ETASParameters,
    earth_radius: float = 6_378.1,
) -> LikelihoodComponents:
    history = tuple(history)
    return LikelihoodComponents(
        point_intensity=point_intensity(
            target, history, m_ref, parameters, earth_radius
        ),
        temporal_intensity=temporal_intensity(
            target.time, history, area, m_ref, parameters
        ),
        compensator=interval_compensator(
            interval_start, target.time, history, area, m_ref, parameters
        ),
    )
