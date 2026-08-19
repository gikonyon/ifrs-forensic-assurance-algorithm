import unittest
import hashlib
import datetime
from models.esg_forensic_engine import (
    register_evidence_document,
    DOSHSIncidentTracker,
    validate_spatial_compliance,
    evaluate_esg_assurance_score,
    classify_assurance_document,
)


class TestAssuranceEngine(unittest.TestCase):

    def test_evidence_vault_hash_generation(self):
        sample_bytes = b"Sample NEMA EIA Audit PDF Content"
        record = register_evidence_document(sample_bytes, "audit.pdf", "NEMA_EIA_LICENCE", "NEMA/LEAD/1042")

        expected_hash = hashlib.sha256(sample_bytes).hexdigest()
        self.assertEqual(record["sha256_hash"], expected_hash)
        self.assertEqual(record["audit_status"], "LOCKED_FOR_ASSURANCE")

    def test_doshs_fatal_sla_calculation(self):
        tracker = DOSHSIncidentTracker("fatal", "Severe machinery accident", "EMP-001")
        payload = tracker.generate_payload("INC-001")

        logged_at = datetime.datetime.strptime(payload["logged_at"], "%Y-%m-%d %H:%M:%S UTC")
        deadline = datetime.datetime.strptime(payload["doshs_deadline"], "%Y-%m-%d %H:%M:%S UTC")

        diff_hours = (deadline - logged_at).total_seconds() / 3600
        self.assertEqual(diff_hours, 24.0)

    def test_spatial_compliance_valid_kenya(self):
        result = validate_spatial_compliance(-1.286389, 36.817223, str(datetime.date.today()))
        self.assertTrue(result["valid"])
        self.assertEqual(result["jurisdiction"], "Kenya")

    def test_spatial_compliance_out_of_bounds(self):
        result = validate_spatial_compliance(51.5074, -0.1278, str(datetime.date.today()))
        self.assertFalse(result["valid"])
        self.assertIn("Kenyan jurisdiction boundaries", result["reason"])

    def test_esg_assurance_scoring(self):
        manifest_full = {
            "EMCA_NEMA_Permit": True,
            "DOSHS_WIBA_Compliance": True,
            "Minimum_Wage_Payroll_Audit": True,
            "Board_E_and_S_Oversight": True,
        }
        eval_full = evaluate_esg_assurance_score(manifest_full)
        self.assertEqual(eval_full["score"], 100)
        self.assertIn("BANKABLE", eval_full["status"])

        manifest_partial = {
            "EMCA_NEMA_Permit": True,
            "DOSHS_WIBA_Compliance": False,
            "Minimum_Wage_Payroll_Audit": False,
            "Board_E_and_S_Oversight": False,
        }
        eval_partial = evaluate_esg_assurance_score(manifest_partial)
        self.assertEqual(eval_partial["score"], 25)
        self.assertIn("UNBANKABLE", eval_partial["status"])

    # --- Regression test for the classifier bug fixed this session ---
    def test_classifier_handles_real_world_phrasing(self):
        se_advisory_text = (
            "SE Advisory Services provided independent third-party reasonable "
            "verification aligned with the ISO 14064-3:2019 standard."
        )
        global_doc_text = (
            "Global Documentation was tasked to provide independent assurance "
            "(limited level) of carbon emissions in accordance with ISO 14064-3."
        )
        ey_text = (
            "Ernst & Young LLP performed a limited assurance engagement in "
            "accordance with International Standard on Assurance Engagements "
            "(ISAE) 3000 (Revised)."
        )

        se_result = classify_assurance_document(se_advisory_text, "se.pdf")
        gd_result = classify_assurance_document(global_doc_text, "gd.pdf")
        ey_result = classify_assurance_document(ey_text, "ey.pdf")

        self.assertNotEqual(se_result["assigned_tier"], "self_reported")
        self.assertNotEqual(gd_result["assigned_tier"], "self_reported")
        self.assertNotEqual(ey_result["assigned_tier"], "self_reported")
        self.assertEqual(se_result["detected_assurance_level"], "reasonable")
        self.assertEqual(gd_result["detected_assurance_level"], "limited")
        self.assertEqual(ey_result["detected_assurance_level"], "limited")


if __name__ == "__main__":
    unittest.main()
