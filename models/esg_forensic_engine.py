"""
Uujuzi Forensic ESG & Assurance Engine
========================================
Single source of truth for all forensic/assurance logic used by app.py,
backend_api.py, and test_assurance_engine.py. 
Upgraded to include professional ReportLab PDF generation capabilities.
"""

import re
import hashlib
import json
import datetime
import io
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


# =====================================================================
# MODULE A — INGESTION & BASELINE SCORING
# =====================================================================

def extract_entity_from_document(text: str, document_name: str = "") -> dict:
    """
    Confirms the uploaded Primary Disclosure Report belongs to the entity
    named on its pages. Tries explicit labels first ("Company:", "Issuer:"),
    then falls back to a PLC/Bank/Group suffix pattern.
    """
    labeled_pattern = r"(?:Company|Entity|Issuer|Client|Prepared for):?\s*([A-Z][A-Za-z0-9&,\.\s]{2,60})"
    match = re.search(labeled_pattern, text)
    if match:
        return {
            "document_name": document_name,
            "detected_entity": match.group(1).strip(),
            "confidence": "high",
        }

    suffix_pattern = r'([A-Z][A-Za-z&,\.\s]{2,60}(?:PLC|Ltd|Limited|Bank|Inc|Group))'
    header_window = text[:2000]
    suffix_match = re.search(suffix_pattern, header_window)
    if suffix_match:
        return {
            "document_name": document_name,
            "detected_entity": suffix_match.group(1).strip(),
            "confidence": "medium",
        }

    return {
        "document_name": document_name,
        "detected_entity": None,
        "confidence": "low",
    }


GREENWASH_KEYWORDS = [
    "net zero", "carbon neutral", "eco friendly", "sustainable future",
    "green initiative", "climate champion", "environmentally conscious",
]

METRIC_PATTERNS = {
    "scope_1": r"Scope\s*1\s*(?:greenhouse\s*gas\s*emissions|emissions)?\s*(?:\(tCO2e\))?[\s:]*([\d,]+(?:\.\d+)?)",
    "scope_2": r"Scope\s*2\s*(?:greenhouse\s*gas\s*emissions|emissions)?\s*(?:\(tCO2e\))?[\s:]*([\d,]+(?:\.\d+)?)",
}


def parse_narrative_claims(text: str) -> dict:
    """
    Module A baseline pass: pulls Scope 1/2 figures where stated and runs a
    lightweight greenwashing heuristic.
    """
    metrics = {}
    for key, pattern in METRIC_PATTERNS.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            metrics[key] = float(m.group(1).replace(",", ""))

    text_lower = text.lower()
    buzzword_count = sum(text_lower.count(kw) for kw in GREENWASH_KEYWORDS)
    has_metrics = bool(metrics)

    if buzzword_count > 10 and not has_metrics:
        risk_level = "HIGH_GREENWASHING_RISK"
    elif buzzword_count > 0 and not has_metrics:
        risk_level = "WATCH — buzzwords present, no supporting metric found"
    else:
        risk_level = "LOW"

    return {
        "metrics_found": metrics,
        "buzzword_count": buzzword_count,
        "risk_level": risk_level,
    }


# =====================================================================
# MODULE B — AUDIT & STANDARDS CROSS-REFERENCE
# =====================================================================

STANDARD_NAME_PATTERNS = {
    "ISO 14064-3": r"ISO\s*14064\s*-?\s*3",
    "ISAE 3000": r"ISAE\)?\s*3000",
    "GRI Standards": r"Global\s+Reporting\s+Initiative|\bGRI\b",
    "TCFD": r"Task\s+Force\s+on\s+Climate|\bTCFD\b",
    "SASB": r"Sustainability\s+Accounting\s+Standards\s+Board|\bSASB\b",
    "CDP": r"\bCDP\b|Carbon\s+Disclosure\s+Project",
    "GHG Protocol": r"GHG\s+Protocol|Greenhouse\s+Gas\s+Protocol",
    "Agreed-Upon Procedures": r"agreed[\s-]upon\s+procedures|\bAUP\b",
}

ASSURANCE_LEVEL_PATTERNS = {
    "reasonable": r"reasonable\s+(level|assurance|verification)",
    "limited": r"limited\s+(level|assurance|verification)",
}

ASSURANCE_ENGAGEMENT_STANDARDS = {"ISO 14064-3", "ISAE 3000", "Agreed-Upon Procedures"}

STANDARD_BASE_TIER = {
    "ISO 14064-3": "independent_verification",
    "ISAE 3000": "external_assurance",
    "Agreed-Upon Procedures": "agreed_upon_procedures",
    "GRI Standards": "framework_alignment",
    "TCFD": "framework_alignment",
    "SASB": "framework_alignment",
    "CDP": "framework_alignment",
    "GHG Protocol": "methodology_reference",
}

TIER_SCORES = {
    ("independent_verification", "reasonable"): 5,
    ("independent_verification", "limited"): 4,
    ("independent_verification", None): 3,
    ("external_assurance", "reasonable"): 5,
    ("external_assurance", "limited"): 4,
    ("external_assurance", None): 3,
    ("agreed_upon_procedures", None): 3,
    ("framework_alignment", None): 2,
    ("methodology_reference", None): 1,
    ("self_reported", None): 0,
}

TIER_LABELS = {
    "independent_verification": "Independent Verification (ISO 14064-3)",
    "external_assurance": "External Assurance (ISAE 3000)",
    "agreed_upon_procedures": "Agreed-Upon Procedures (Specific Testing)",
    "framework_alignment": "Framework Alignment (non-assurance)",
    "methodology_reference": "Methodology Reference Only",
    "self_reported": "Self-Reported / Unaudited",
}


def classify_assurance_document(text: str, document_name: str = "") -> dict:
    """
    Detects standard invocations and assurance levels safely handling boilerplate text.
    """
    detected_standards = [
        name for name, pattern in STANDARD_NAME_PATTERNS.items()
        if re.search(pattern, text, re.IGNORECASE)
    ]

    opening_window = text[:1200]
    detected_level = None
    for level, pattern in ASSURANCE_LEVEL_PATTERNS.items():
        if re.search(pattern, opening_window, re.IGNORECASE):
            detected_level = level
            break
    if detected_level is None:
        for level, pattern in ASSURANCE_LEVEL_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                detected_level = level
                break

    if not detected_standards:
        best_tier, best_level, best_score = "self_reported", None, 0
    else:
        candidates = []
        for standard in detected_standards:
            base_tier = STANDARD_BASE_TIER[standard]
            level_for_this = detected_level if standard in ASSURANCE_ENGAGEMENT_STANDARDS else None
            score = TIER_SCORES.get((base_tier, level_for_this), TIER_SCORES.get((base_tier, None), 0))
            candidates.append((base_tier, level_for_this, score))
        best_tier, best_level, best_score = max(candidates, key=lambda c: c[2])

    tier_label = TIER_LABELS[best_tier]
    if best_level:
        tier_label += f" — {best_level.capitalize()} Assurance"

    verifier_match = re.search(
        r"(Ernst\s*&\s*Young|EY|KPMG|PwC|Deloitte|SGS|Bureau\s+Veritas|"
        r"SE\s+Advisory\s+Services|Schneider\s+Electric|Global\s+Documentation)",
        text, re.IGNORECASE
    )
    verifier = verifier_match.group(0) if verifier_match else "Unknown / not detected"

    return {
        "document_name": document_name,
        "detected_standards": detected_standards or ["None detected"],
        "detected_assurance_level": best_level,
        "assigned_tier": best_tier,
        "tier_label": tier_label,
        "tier_score": best_score,
        "verifier": verifier,
    }


def cross_reference_claims(narrative_claims: dict, assurance_documents: list) -> dict:
    """Cross-references primary claims against assurance documents."""
    metrics = narrative_claims.get("metrics_found", {})
    combined_text = " ".join(doc.get("text", "") for doc in assurance_documents)

    results = {}
    for metric_name, value in metrics.items():
        value_str = f"{value:,.0f}"
        value_str_alt = f"{value:.0f}"
        corroborated = value_str in combined_text or value_str_alt in combined_text
        results[metric_name] = {
            "claimed_value": value,
            "corroborated_in_assurance_docs": corroborated,
        }

    return {
        "claims_checked": len(results),
        "claims_corroborated": sum(1 for r in results.values() if r["corroborated_in_assurance_docs"]),
        "detail": results,
    }


# =====================================================================
# MODULE C — QUANTITATIVE DATA PACK RECONCILIATION
# =====================================================================

def score_data_pack_metrics(df: pd.DataFrame, assured_marker: str = "^") -> dict:
    """Scores each row of a data pack against the assurance marker."""
    total_metrics = len(df)
    assured_count = 0
    row_details = []

    for _, row in df.iterrows():
        if "Description" in df.columns:
            desc = str(row.get("Description", ""))
        elif len(row) > 1:
            desc = " ".join(str(v) for v in row.values if pd.notna(v))
        else:
            desc = str(row.iloc[0]) if len(row) else ""

        is_assured = assured_marker in desc
        if is_assured:
            assured_count += 1
        row_details.append({
            "Metric": desc[:150],
            "Assured": "Yes" if is_assured else "No",
        })

    ratio = round(assured_count / total_metrics, 3) if total_metrics > 0 else 0.0
    return {
        "total_metrics_scanned": total_metrics,
        "assured_metrics": assured_count,
        "unaudited_metrics": total_metrics - assured_count,
        "assured_ratio": ratio,
        "row_level_detail": row_details,
    }


def reconcile_data_pack_totals(narrative_claims: dict, df: pd.DataFrame,
                                value_column: str = "Value", metric_column: str = "Description") -> dict:
    """Reconciles narrative totals against underlying data pack rows."""
    if value_column not in df.columns:
        return {"reconciled": None, "reason": f"No '{value_column}' column in data pack."}

    metrics = narrative_claims.get("metrics_found", {})
    checks = {}
    for metric_name, claimed_total in metrics.items():
        keyword = metric_name.replace("_", " ")
        if metric_column in df.columns:
            matching_rows = df[df[metric_column].astype(str).str.contains(keyword, case=False, na=False)]
        else:
            matching_rows = df

        underlying_sum = pd.to_numeric(matching_rows[value_column], errors="coerce").sum()
        difference = round(claimed_total - underlying_sum, 2)
        checks[metric_name] = {
            "claimed_total": claimed_total,
            "underlying_data_pack_sum": round(float(underlying_sum), 2),
            "difference": difference,
            "reconciled": abs(difference) < 0.01,
        }

    return {
        "checks_performed": len(checks),
        "all_reconciled": all(c["reconciled"] for c in checks.values()) if checks else None,
        "detail": checks,
    }


# =====================================================================
# MODULE D — GIS SPATIAL AUDIT & BOUNDARY MAPPING
# =====================================================================

def evaluate_esg_claim(entity: str, claim_id: str, category: str, metric: str,
                        year: int, polygon: str, gis_data: dict) -> dict:
    """Evaluates location-bound physical claims."""
    current_year = 2026
    if year < 2017 or year > current_year:
        return {"Error": "Claim year out of supported historical GIS verification window (2017-2026)."}

    discrepancy_detected = False
    trust_status = "Verified True"
    audit_notes = "Spatial footprints and temporal tracking align with disclosures."

    if category == "Environmental" and "forest" in metric.lower():
        baseline_ndvi = gis_data.get('baseline_ndvi', 0.5)
        current_ndvi = gis_data.get('current_ndvi', 0.3)
        if current_ndvi < baseline_ndvi:
            discrepancy_detected = True
            trust_status = "High Discrepancy (Greenwashing Risk)"
            audit_notes = f"Sentinel/Landsat time-series (2017-{current_year}) shows declining canopy density."

    elif category == "Social" and "school" in metric.lower():
        is_constructed = gis_data.get('structure_built', False)
        is_operational = gis_data.get('operational_foot_traffic', False)
        if is_constructed and not is_operational:
            trust_status = "Partial Reality (Constructed, Non-Functional)"
            audit_notes = "Building footprint verified via optical imagery, but lacks operational activity proxies."
        elif not is_constructed:
            discrepancy_detected = True
            trust_status = "False Claim (Undeveloped Land)"
            audit_notes = "Historical imagery confirms land remains vacant or unbuilt during claimed period."

    return {
        "Entity": entity,
        "ClaimID": claim_id,
        "Category": category,
        "Metric": metric,
        "Year": year,
        "SpatialPolygon": polygon,
        "TrustStatus": trust_status,
        "Findings": audit_notes,
        "DiscrepancyFlag": discrepancy_detected,
    }


def validate_spatial_compliance(latitude: float, longitude: float, observation_date: str) -> dict:
    """Validates spatial coordinates and freshness SLAs."""
    is_in_kenya = (-4.7 <= latitude <= 5.5) and (33.9 <= longitude <= 41.9)

    try:
        obs_date = datetime.datetime.strptime(observation_date, "%Y-%m-%d").date()
    except ValueError:
        return {"valid": False, "reason": "Invalid date format. Use YYYY-MM-DD."}

    days_diff = (datetime.date.today() - obs_date).days

    if not is_in_kenya:
        return {"valid": False, "reason": "Location falls outside Kenyan jurisdiction boundaries."}
    if days_diff > 30:
        return {"valid": False, "reason": "Evidence stale. Field observation exceeds 30-day freshness SLA."}

    return {"valid": True, "jurisdiction": "Kenya", "status": "EUDR / NEMA CLEAR"}


EXPECTED_BOUNDARIES = [
    "Scope 1", "Scope 2", "Scope 3 Category 6 (Business Travel)",
    "Scope 3 Category 8 (Purchased Goods/Data Centres)",
    "Scope 3 Financed Emissions", "Scope 3 Facilitated Emissions",
]

BOUNDARY_PATTERNS = {
    "Scope 1": r"Scope\s*1\b",
    "Scope 2": r"Scope\s*2\b",
    "Scope 3 Category 6 (Business Travel)": r"business\s+travel|Category\s*6",
    "Scope 3 Category 8 (Purchased Goods/Data Centres)": r"data\s+centre|Category\s*8",
    "Scope 3 Financed Emissions": r"financed\s+emissions",
    "Scope 3 Facilitated Emissions": r"facilitated\s+emissions",
}


def check_assurance_coverage(documents: list) -> dict:
    """Checks emission boundary coverage."""
    covered = {b: [] for b in EXPECTED_BOUNDARIES}
    for doc in documents:
        text = doc.get("text", "")
        for boundary, pattern in BOUNDARY_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                covered[boundary].append(doc.get("document_name", "unknown"))

    gaps = [b for b, docs in covered.items() if not docs]
    return {
        "coverage_complete": len(gaps) == 0,
        "covered_boundaries": {b: docs for b, docs in covered.items() if docs},
        "uncovered_boundaries": gaps,
    }


def detect_restatements(text: str, document_name: str = "") -> dict:
    """Flags prior-year restatements."""
    restatement_keywords = ["restated", "prior year adjustment", "reclassification", "previously reported"]
    found_excerpts = [
        sentence.strip()
        for sentence in text.split(".")
        if any(kw in sentence.lower() for kw in restatement_keywords)
    ]
    return {
        "document_name": document_name,
        "restatement_disclosed": len(found_excerpts) > 0,
        "restatement_excerpts": found_excerpts[:5],
    }


# =====================================================================
# REGULATORY & COMPLIANCE LAYER
# =====================================================================

def register_evidence_document(file_bytes: bytes, filename: str, document_type: str, issuer_id: str) -> dict:
    """Hashes and locks uploaded evidence document."""
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    return {
        "document_name": filename,
        "document_type": document_type,
        "issuer_id": issuer_id,
        "sha256_hash": file_hash,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "audit_status": "LOCKED_FOR_ASSURANCE",
    }


class DOSHSIncidentTracker:
    """Tracks workplace incident SLA deadlines."""
    SLA_HOURS = {"fatal": 24, "non_fatal": 168}

    def __init__(self, incident_type: str, description: str, employee_id: str):
        incident_type = incident_type.lower()
        if incident_type not in self.SLA_HOURS:
            raise ValueError("incident_type must be 'fatal' or 'non_fatal'")
        self.incident_type = incident_type
        self.description = description
        self.employee_id = employee_id

    def generate_payload(self, incident_id: str) -> dict:
        sla_hours = self.SLA_HOURS[self.incident_type]
        logged_at = datetime.datetime.now(datetime.timezone.utc)
        deadline = logged_at + datetime.timedelta(hours=sla_hours)

        payload = {
            "incident_id": incident_id,
            "employee_id": self.employee_id,
            "incident_type": self.incident_type.upper(),
            "logged_at": logged_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "doshs_deadline": deadline.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "description": self.description,
        }
        payload["hash"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()[:12]
        return payload


def evaluate_esg_assurance_score(manifest: dict) -> dict:
    """Scores lending-readiness manifest."""
    weight = 100 / max(len(manifest), 1)
    score = round(sum(weight for v in manifest.values() if v))
    status = "BANKABLE — meets core compliance gates" if score >= 75 else "CONDITIONALLY BANKABLE — gaps require remediation"
    return {"score": score, "status": status, "manifest_detail": manifest}


# =====================================================================
# MODULE E — COMPREHENSIVE REPORT SYNTHESIZER & PDF EXPORT
# =====================================================================

def build_verification_report(entity_name: str, primary_disclosure_text: str, primary_disclosure_name: str,
                                supporting_documents: list, data_pack_dataframes: list = None,
                                gis_claims: list = None) -> dict:
    """Compiles Modules A-D into one verification report dictionary."""
    entity_res = extract_entity_from_document(primary_disclosure_text, primary_disclosure_name)
    narrative_res = parse_narrative_claims(primary_disclosure_text)
    restatement_res = detect_restatements(primary_disclosure_text, primary_disclosure_name)

    document_classifications = [
        classify_assurance_document(doc.get("text", ""), doc.get("document_name", ""))
        for doc in supporting_documents
    ]
    coverage_res = check_assurance_coverage(supporting_documents)
    cross_ref_res = cross_reference_claims(narrative_res, supporting_documents)

    dp_summary = {"total_metrics_scanned": 0, "assured_metrics": 0, "assured_ratio": 0.0}
    reconciliation_results = []
    if data_pack_dataframes:
        for dp in data_pack_dataframes:
            df = dp.get("dataframe", pd.DataFrame())
            res = score_data_pack_metrics(df)
            dp_summary["total_metrics_scanned"] += res["total_metrics_scanned"]
            dp_summary["assured_metrics"] += res["assured_metrics"]
            reconciliation_results.append({
                "document_name": dp.get("document_name", ""),
                "reconciliation": reconcile_data_pack_totals(narrative_res, df),
            })
        if dp_summary["total_metrics_scanned"] > 0:
            dp_summary["assured_ratio"] = round(
                dp_summary["assured_metrics"] / dp_summary["total_metrics_scanned"], 3
            )

    gis_results = [evaluate_esg_claim(**claim) for claim in gis_claims] if gis_claims else []

    all_tier_scores = [d["tier_score"] for d in document_classifications]
    max_possible = len(all_tier_scores) * 5 if all_tier_scores else 1
    aggregate_score = sum(all_tier_scores)

    final_status = (
        "PASSED & VERIFIED"
        if coverage_res["coverage_complete"] and not restatement_res["restatement_disclosed"]
        else "REVIEW REQUIRED: Gaps Detected"
    )

    return {
        "EntityName": entity_name,
        "PrimaryReportEntityAudit": entity_res,
        "NarrativeClaimScreen": narrative_res,
        "AssuranceDocumentClassifications": document_classifications,
        "AssuranceBoundaryCoverage": coverage_res,
        "ClaimCrossReference": cross_ref_res,
        "RestatementCheck": restatement_res,
        "DataPackAuditSummary": dp_summary,
        "DataPackReconciliation": reconciliation_results,
        "GISClaimResults": gis_results,
        "AggregateAssuranceScore": f"{aggregate_score} / {max_possible}",
        "FinalComplianceStatus": final_status,
    }


def generate_forensic_pdf_report(report_data: dict) -> bytes:
    """
    Generates a professional downloadable PDF report from the verification output.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1b4332'), spaceAfter=8
    )
    heading_style = ParagraphStyle(
        'SectionHeading', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#2d6a4f'), spaceBefore=8, spaceAfter=4
    )
    body_style = styles['Normal']
    
    # Title Section
    story.append(Paragraph("Uujuzi Forensic ESG & Assurance Report", title_style))
    story.append(Paragraph(f"<b>Entity Evaluated:</b> {report_data.get('EntityName', 'N/A')}", body_style))
    story.append(Paragraph(f"<b>Overall Compliance Status:</b> {report_data.get('FinalComplianceStatus', 'N/A')}", body_style))
    story.append(Spacer(1, 8))
    
    # Summary Table
    story.append(Paragraph("Verification Summary Metrics", heading_style))
    table_data = [
        ["Audit Component", "Status / Findings"],
        ["Aggregate Assurance Score", report_data.get('AggregateAssuranceScore', '0 / 0')],
        ["Data Pack Assured Ratio", f"{report_data.get('DataPackAuditSummary', {}).get('assured_ratio', 0.0) * 100}%"],
        ["Boundary Coverage Complete", str(report_data.get('AssuranceBoundaryCoverage', {}).get('coverage_complete', False))],
    ]
    t = Table(table_data, colWidths=[200, 300])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e9f5ed')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#1b4332')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d8d8d8'))
    ]))
    story.append(t)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
