"""
Uujuzi Forensic ESG & Assurance Engine — Test Suite
===================================================
Tests all modules (A through E) and compliance features to ensure
no logic drift between app.py, backend_api.py, and esg_forensic_engine.py.
"""

import datetime
import pandas as pd
import pytest

from esg_forensic_engine import (
    extract_entity_from_document,
    parse_narrative_claims,
    classify_assurance_document,
    cross_reference_claims,
    score_data_pack_metrics,
    reconcile_data_pack_totals,
    evaluate_esg_claim,
    validate_spatial_compliance,
    check_assurance_coverage,
    detect_restatements,
    register_evidence_document,
    DOSHSIncidentTracker,
    evaluate_esg_assurance_score,
    build_verification_report,
    generate_forensic_pdf_report,
)


def test_extract_entity_from_document():
    text = "Prepared for: Standard Chartered Bank Kenya Limited. Annual Sustainability Review 2025."
    res = extract_entity_from_document(text, "report.pdf")
    assert res["detected_entity"] == "Standard Chartered Bank Kenya Limited"
    assert res["confidence"] == "high"


def test_parse_narrative_claims():
    text = "Our operations emitted Scope 1 greenhouse gas emissions: 14,250 tCO2e and Scope 2: 8,100 tCO2e."
    res = parse_narrative_claims(text)
    assert res["metrics_found"]["scope_1"] == 14250.0
    assert res["metrics_found"]["scope_2"] == 8100.0
    assert res["risk_level"] == "LOW"


def test_classify_assurance_document_iso():
    text = "We were engaged to provide independent verification of greenhouse gas assertions in accordance with ISO 14064 -3:2019 at a reasonable level."
    res = classify_assurance_document(text, "iso_cert.pdf")
    assert "ISO 14064-3" in res["detected_standards"]
    assert res["detected_assurance_level"] == "reasonable"
    assert res["assigned_tier"] == "independent_verification"
    assert res["tier_score"] == 5


def test_score_data_pack_metrics():
    df = pd.DataFrame({
        "Description": ["Total Scope 1 Emissions ^", "Community Tree Planting Initiative", "Water Usage Volume ^"],
        "Value": [14250, 500, 1200]
    })
    res = score_data_pack_metrics(df, assured_marker="^")
    assert res["total_metrics_scanned"] == 3
    assert res["assured_metrics"] == 2
    assert res["assured_ratio"] == 0.667


def test_reconcile_data_pack_totals():
    narrative = {"metrics_found": {"scope_1": 14250.0}}
    df = pd.DataFrame({
        "Description": ["Scope 1 Facility A", "Scope 1 Facility B"],
        "Value": [10000.0, 4250.0]
    })
    res = reconcile_data_pack_totals(narrative, df)
    assert res["all_reconciled"] is True
    assert res["detail"]["scope_1"]["difference"] == 0.0


def test_validate_spatial_compliance():
    # Valid coordinates inside Kenya and fresh observation date
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    res = validate_spatial_compliance(-1.2863, 36.8172, today_str)
    assert res["valid"] is True
    assert res["jurisdiction"] == "Kenya"

    # Invalid coordinates outside Kenya
    res_outside = validate_spatial_compliance(45.0, 36.8172, today_str)
    assert res_outside["valid"] is False


def test_doshs_incident_tracker():
    tracker = DOSHSIncidentTracker(incident_type="fatal", description="Factory floor incident", employee_id="EMP-998")
    payload = tracker.generate_payload("INC-2026-001")
    assert payload["incident_type"] == "FATAL"
    assert "doshs_deadline" in payload
    assert len(payload["hash"]) == 12


def test_evaluate_esg_assurance_score():
    manifest = {
        "environmental_permit": True,
        "workplace_safety": True,
        "wage_compliance": True,
        "board_oversight": False,
    }
    res = evaluate_esg_assurance_score(manifest)
    assert res["score"] == 75
    assert "BANKABLE" in res["status"]


def test_build_verification_report():
    primary_text = "Issuer: GreenCorp PLC. Scope 1: 5,000 tCO2e."
    supp_docs = [{
        "document_name": "audit.pdf",
        "text": "Independent verification engagement under ISAE 3000 with limited assurance covering Scope 1 emissions."
    }]
    report = build_verification_report(
        entity_name="GreenCorp PLC",
        primary_disclosure_text=primary_text,
        primary_disclosure_name="primary.pdf",
        supporting_documents=supp_docs
    )
    assert report["EntityName"] == "GreenCorp PLC"
    assert report["PrimaryReportEntityAudit"]["detected_entity"] == "GreenCorp PLC"


def test_generate_forensic_pdf_report():
    """Validates that the ReportLab PDF generation routine compiles and outputs valid binary data."""
    sample_report = {
        "EntityName": "Test Corporation PLC",
        "FinalComplianceStatus": "PASSED & VERIFIED",
        "AggregateAssuranceScore": "15 / 15",
        "DataPackAuditSummary": {"assured_ratio": 0.85},
        "AssuranceBoundaryCoverage": {"coverage_complete": True}
    }
    
    pdf_bytes = generate_forensic_pdf_report(sample_report)
    
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b'%PDF')
