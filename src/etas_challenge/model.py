"""Conditional intensity for the native ETAS point process."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from etas_challenge.kernels import triggering_rate
from etas_challenge.parameters import ETASParameters


@dataclass(frozen=True, slots=True)
class Event:
    magnitude: float
    time: float
    x: float
    y: float


def conditional_intensity(
    time: float,
    x: float,
    y: float,
    history: Iterable[Event],
    m_ref: float,
    parameters: ETASParameters,
) -> float:
    intensity = parameters.mu
    for event in history:
        if event.time >= time:
            continue
        intensity += triggering_rate(
            event.magnitude,
            time - event.time,
            x - event.x,
            y - event.y,
            m_ref,
            parameters,
        )
    return intensity
