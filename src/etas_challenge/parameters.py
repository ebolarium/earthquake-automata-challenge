"""Physical and transformed parameters for the native ETAS model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ETASParameters:
    mu: float
    k0: float
    a: float
    c: float
    omega: float
    tau: float
    d: float
    gamma: float
    rho: float

    def __post_init__(self) -> None:
        positive = {
            "mu": self.mu,
            "k0": self.k0,
            "c": self.c,
            "tau": self.tau,
            "d": self.d,
            "rho": self.rho,
        }
        for name, value in positive.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.omega > 0:
            raise ValueError("omega must be non-positive in the reference model")

    @classmethod
    def from_transformed(
        cls,
        *,
        log10_mu: float,
        log10_k0: float,
        a: float,
        log10_c: float,
        omega: float,
        log10_tau: float,
        log10_d: float,
        gamma: float,
        rho: float,
    ) -> ETASParameters:
        return cls(
            mu=10.0**log10_mu,
            k0=10.0**log10_k0,
            a=a,
            c=10.0**log10_c,
            omega=omega,
            tau=10.0**log10_tau,
            d=10.0**log10_d,
            gamma=gamma,
            rho=rho,
        )

    @property
    def productivity_exponent(self) -> float:
        return self.a - self.rho * self.gamma
