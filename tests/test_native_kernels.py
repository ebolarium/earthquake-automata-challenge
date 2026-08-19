import math
import sys
import unittest
from pathlib import Path

from scipy.integrate import quad

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.kernels import (
    branching_ratio,
    expected_direct_aftershocks,
    magnitude_density,
    spatial_integral_disk,
    spatial_kernel,
    temporal_integral,
    temporal_kernel,
    triggering_rate,
)
from etas_challenge.model import Event, conditional_intensity
from etas_challenge.parameters import ETASParameters


REFERENCE = ETASParameters.from_transformed(
    log10_mu=-6.3329886729199405,
    log10_k0=-2.6717871682913943,
    a=1.5556888441764327,
    log10_c=-2.79828186440062,
    omega=-0.06185408129678495,
    log10_tau=3.723786279418681,
    log10_d=-0.7725791509539909,
    gamma=1.010873536606162,
    rho=0.5565963092026862,
)
M_REF = 2.5
BETA = 2.1471442086213064


class NativeKernelTests(unittest.TestCase):
    def test_transformed_parameters_and_productivity_exponent(self):
        self.assertAlmostEqual(REFERENCE.mu, 10**-6.3329886729199405)
        self.assertAlmostEqual(REFERENCE.tau, 10**3.723786279418681)
        self.assertAlmostEqual(
            REFERENCE.productivity_exponent,
            REFERENCE.a - REFERENCE.rho * REFERENCE.gamma,
        )

    def test_temporal_integral_matches_independent_quadrature(self):
        expected, _ = quad(lambda value: temporal_kernel(value, REFERENCE), 0, 3650)
        actual = temporal_integral(0, 3650, REFERENCE)
        self.assertAlmostEqual(actual, expected, places=10)

    def test_spatial_integral_matches_independent_radial_quadrature(self):
        magnitude = 5.0
        radius = 250.0
        expected, _ = quad(
            lambda value: 2
            * math.pi
            * value
            * spatial_kernel(value, 0, magnitude, M_REF, REFERENCE),
            0,
            radius,
        )
        actual = spatial_integral_disk(radius, magnitude, M_REF, REFERENCE)
        self.assertAlmostEqual(actual, expected, places=10)

    def test_branching_ratio_matches_magnitude_quadrature(self):
        # The omitted exponential tail above M_ref + 100 is below 1e-49.
        expected, _ = quad(
            lambda magnitude: magnitude_density(magnitude, M_REF, BETA)
            * expected_direct_aftershocks(magnitude, M_REF, REFERENCE),
            M_REF,
            M_REF + 100.0,
        )
        self.assertAlmostEqual(branching_ratio(BETA, REFERENCE), expected, places=9)

    def test_triggering_is_causal_and_intensity_sums_history(self):
        parent = Event(magnitude=4.5, time=1.0, x=2.0, y=3.0)
        future = Event(magnitude=7.0, time=5.0, x=2.0, y=3.0)
        expected = REFERENCE.mu + triggering_rate(
            parent.magnitude,
            3.0,
            1.0,
            1.0,
            M_REF,
            REFERENCE,
        )
        actual = conditional_intensity(
            4.0,
            3.0,
            4.0,
            [parent, future],
            M_REF,
            REFERENCE,
        )
        self.assertAlmostEqual(actual, expected)
        self.assertEqual(
            triggering_rate(4.0, 0.0, 0.0, 0.0, M_REF, REFERENCE),
            0.0,
        )

    def test_invalid_branching_ratio_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "beta >"):
            branching_ratio(REFERENCE.productivity_exponent, REFERENCE)


if __name__ == "__main__":
    unittest.main()
