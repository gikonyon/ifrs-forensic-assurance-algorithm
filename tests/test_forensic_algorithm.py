import unittest

from src.forensic_algorithm import (
    assess_climate,
    assess_governance,
    calculate_dqs,
    classify_assurance_state,
    greenhouse_gas_intensity,
    hhi,
    verify_metric,
)


class TestGovernance(unittest.TestCase):

    def test_parity_hhi(self):
        self.assertAlmostEqual(hhi([0.5, 0.5]), 0.5)

    def test_gender_share_gap(self):
        result = assess_governance(50, 50)
        self.assertAlmostEqual(result.gender_share_gap, 0.0)

    def test_two_thirds_benchmark(self):
        result = assess_governance(33, 67)
        self.assertTrue(result.female_meets_two_thirds)


class TestClimate(unittest.TestCase):

    def test_intensity(self):
        self.assertAlmostEqual(
            greenhouse_gas_intensity(100, 50, 1000),
            0.15,
        )

    def test_climate_result(self):
        result = assess_climate(100, 50, 1000)
        self.assertEqual(result.total_scope1_scope2_tco2e, 150)
        self.assertTrue(result.arithmetic_valid)


class TestDQS(unittest.TestCase):

    def test_perfect_score(self):
        result = calculate_dqs(100, 100, 100, 100, 100)
        self.assertEqual(result.score, 100)
        self.assertEqual(result.tier, "ASSURANCE_READY")


class TestVerification(unittest.TestCase):

    def test_pass(self):
        result = verify_metric(
            "Test",
            100,
            100,
            source_exists=True,
            evidence_exists=True,
        )
        self.assertEqual(result.status, "PASS")

    def test_variance_exception(self):
        result = verify_metric(
            "Test",
            100,
            110,
            source_exists=True,
            evidence_exists=True,
            tolerance_percentage=1,
        )
        self.assertEqual(result.status, "EXCEPTION")
        self.assertEqual(result.exception_code, "EX-VARIANCE")


class TestRisk(unittest.TestCase):

    def test_high_score(self):
        self.assertEqual(classify_assurance_state(96), "ALPHA")

    def test_low_score(self):
        self.assertEqual(classify_assurance_state(0), "ZINC")


if __name__ == "__main__":
    unittest.main()
