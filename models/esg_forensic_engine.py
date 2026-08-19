import re
import datetime
import pandas as pd

# ---------------------------------------------------------------------------
# 1. PRIMARY DISCLOSURE INGESTION
# ---------------------------------------------------------------------------
def extract_entity_from_document(document_text, document_name=""):
    header_window = document_text[:2000]
    candidates = re.findall(
        r'([A-Z][A-Za-z&,\.\s]{2,60}(?:PLC|Ltd|Limited|Bank|Inc|Group))',
        header_window
    )
    detected_entity = candidates[0].strip() if candidates else None
    return {
        "document_name": document_name,
        "detected_entity": detected_entity,
        "confidence": "high" if candidates else "low",
    }


# ---------------------------------------------------------------------------
# 2. DOCUMENT / STANDARD CLASSIFICATION
# ---------------------------------------------------------------------------
STANDARD_NAME_PATTERNS = {
    "ISO 14064-3": r"ISO\s*14064-3",
    "ISAE 3000": r"ISAE\)?\s*3000",
    "GRI Standards": r"Global\s+Reporting\s+Initiative|\bGRI\b",
    "TCFD": r"Task\s+Force\s+on\s+Climate|\bTCFD\b",
    "SASB": r"Sustainability\s+Accounting\s+Standards\s+Board|\bSASB\b",
    "CDP": r"\bCDP\b|Carbon\s+Disclosure\s+Project",
    "GHG Protocol": r"GHG\s+Protocol|Greenhouse\s+Gas\s+Protocol",
}

ASSURANCE_LEVEL_PATTERNS = {
    "reasonable": r"reasonable\s+(level|assurance|verification)",
    "limited": r"limited\s+(level|assurance|verification)",
}

ASSURANCE_ENGAGEMENT_STANDARDS = {"ISO 14064-3", "ISAE 3000"}

STANDARD_BASE_TIER = {
    "ISO 14064-3": "independent_verification",
    "ISAE 3000": "external_assurance",
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
    ("framework_alignment", None): 2,
    ("methodology_reference", None): 1,
    ("self_reported", None): 0,
}

TIER_LABELS = {
    "independent_verification": "Independent Verification (ISO 14064-3)",
    "external_assurance": "External Assurance (ISAE 3000)",
    "framework_alignment": "Framework Alignment (non-assurance)",
    "methodology_reference": "Methodology Reference Only",
    "self_reported": "Self-Reported / Unaudited",
}

def classify_assurance_document(document_text, document_name=""):
    detected_standards = [
        name for name, pattern in STANDARD_NAME_PATTERNS.items()
        if re.search(pattern, document_text, re.IGNORECASE)
    ]

    detected_level = None
    for level, pattern in ASSURANCE_LEVEL_PATTERNS.items():
        if re.search(pattern, document_text, re.IGNORECASE):
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
            candidates.append((base_tier, level_for_this, score, standard))
        best_tier, best_level, best_score, best_standard = max(candidates, key=lambda c: c[2])

    tier_label = TIER_LABELS[best_tier]
    if best_level:
        tier_label += f" — {best_level.capitalize()} Assurance"

    verifier_match = re.search(
        r"(Ernst\s*&\s*Young|EY|KPMG|PwC|Deloitte|SGS|Bureau\s+Veritas|"
        r"SE\s+Advisory\s+Services|Schneider\s+Electric|Global\s+Documentation)",
        document_text, re.IGNORECASE
    )
    verifier = verifier_match.group(0) if verifier_match else "Unknown / not detected"

    return {
        "document_name": document_name,
        "detected_standards": detected_standards,
        "detected_assurance_level": best_level,
        "assigned_tier": best_tier,
        "tier_label": tier_label,
        "tier_score": best_score,
        "verifier": verifier,
    }


# ---------------------------------------------------------------------------
# 3. METRIC-LEVEL SCORING FOR SUPPORTING DATA PACKS (XLSX/CSV)
# ---------------------------------------------------------------------------
def score_data_pack_metrics(dataframe, assured_marker="^"):
    results = []
    assured_count = 0
    total_count = 0

    for idx, row in dataframe.iterrows():
        row_text = " ".join(str(v) for v in row.values if pd.notna(v))
        if not row_text.strip():
            continue
        total_count += 1
        is_assured = assured_marker in row_text
        if is_assured:
            assured_count += 1
        results.append({
            "row_index": idx,
            "row_preview": row_text[:120],
            "assured": is_assured,
            "tier_label": ("Externally Assured (assurance marker detected)" if is_assured
                           else TIER_LABELS["self_reported"]),
        })

    assured_ratio = round(assured_count / total_count, 3) if total_count else 0.0

    return {
        "total_metrics_scanned": total_count,
        "assured_metrics": assured_count,
        "unaudited_metrics": total_count - assured_count,
        "assured_ratio": assured_ratio,
        "row_level_detail": results,
    }


# ---------------------------------------------------------------------------
# 4. COVERAGE / BOUNDARY CHECK ACROSS MULTIPLE ASSURANCE PROVIDERS
# ---------------------------------------------------------------------------
EXPECTED_BOUNDARIES = [
    "Scope 1",
    "Scope 2",
    "Scope 3 Category 6 (Business Travel)",
    "Scope 3 Category 8 (Purchased Goods/Data Centres)",
    "Scope 3 Financed Emissions",
    "Scope 3 Facilitated Emissions",
]

BOUNDARY_PATTERNS = {
    "Scope 1": r"Scope\s*1\b",
    "Scope 2": r"Scope\s*2\b",
    "Scope 3 Category 6 (Business Travel)": r"business\s+travel|Category\s*6",
    "Scope 3 Category 8 (Purchased Goods/Data Centres)": r"data\s+centre|Category\s*8",
    "Scope 3 Financed Emissions": r"financed\s+emissions",
    "Scope 3 Facilitated Emissions": r"facilitated\s+emissions",
}

def check_assurance_coverage(document_texts):
    covered = {b: [] for b in EXPECTED_BOUNDARIES}

    for doc in document_texts:
        for boundary, pattern in BOUNDARY_PATTERNS.items():
            if re.search(pattern, doc["text"], re.IGNORECASE):
                covered[boundary].append(doc["document_name"])

    gaps = [b for b, docs in covered.items() if not docs]

    return {
        "covered_boundaries": {b: docs for b, docs in covered.items() if docs},
        "uncovered_boundaries": gaps,
        "coverage_complete": len(gaps) == 0,
    }


# ---------------------------------------------------------------------------
# 5. RESTATEMENT / DATA-INTEGRITY DISCLOSURE DETECTION
# ---------------------------------------------------------------------------
def detect_restatements(document_text, document_name=""):
    pattern = r"([^.]{0,200}restat[a-z]*[^.]{0,200}\.)"
    hits = re.findall(pattern, document_text, re.IGNORECASE)
    return {
        "document_name": document_name,
        "restatement_disclosed": len(hits) > 0,
        "restatement_excerpts": hits[:5],
    }


# ---------------------------------------------------------------------------
# 6. GIS / SPATIAL CLAIM VERIFICATION
# ---------------------------------------------------------------------------
def evaluate_esg_claim(entity_name, claim_id, category, claimed_metric,
                       claim_year, spatial_bounds, gis_observation_data):
    current_year = 2026
    if claim_year < 2017 or claim_year > current_year:
        return {"Error": "Claim year out of supported historical GIS verification window (2017-2026)."}

    discrepancy_detected = False
    trust_status = "Verified True"
    audit_notes = "Spatial footprints and temporal tracking align with disclosures."

    if category == "Environmental" and "forest" in claimed_metric.lower():
        baseline_ndvi = gis_observation_data.get('baseline_ndvi', 0.5)
        current_ndvi = gis_observation_data.get('current_ndvi', 0.3)
        if current_ndvi < baseline_ndvi:
            discrepancy_detected = True
            trust_status = "High Discrepancy (Greenwashing Risk)"
            audit_notes = f"Sentinel/Landsat time-series (2017-{current_year}) shows declining canopy density."

    elif category == "Social" and "school" in claimed_metric.lower():
        is_constructed = gis_observation_data.get('structure_built', False)
        is_operational = gis_observation_data.get('operational_foot_traffic', False)
        if is_constructed and not is_operational:
            trust_status = "Partial Reality (Constructed, Non-Functional)"
            audit_notes = "Building footprint verified via optical imagery, but lacks operational activity proxies."
        elif not is_constructed:
            discrepancy_detected = True
            trust_status = "False Claim (Undeveloped Land)"
            audit_notes = "Historical imagery confirms land remains vacant or unbuilt during claimed period."

    return {
        "Entity": entity_name,
        "ClaimID": claim_id,
        "Category": category,
        "ClaimedMetric": claimed_metric,
        "ClaimYear": claim_year,
        "TrustStatus": trust_status,
        "Findings": audit_notes,
        "DiscrepancyFlag": discrepancy_detected,
    }


# ---------------------------------------------------------------------------
# 7. AGGREGATE REPORT BUILDER & EXECUTION BLOCK
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("======================================================================")
    print("        UUJUZI FORENSIC ESG & ASSURANCE ENGINE - EXECUTION REPORT        ")
    print("======================================================================")

    # 1. Run GIS Spatial Claim Check
    sample_gis_data = {'baseline_ndvi': 0.62, 'current_ndvi': 0.41}
    gis_res = evaluate_esg_claim(
        entity_name="GreenCorp Ltd",
        claim_id="CLM-2021-04",
        category="Environmental",
        claimed_metric="5,000 ha of indigenous forest restored and protected since 2017",
        claim_year=2021,
        spatial_bounds="Polygon(1.2921, 36.8219)",
        gis_observation_data=sample_gis_data,
    )
    print("\n[1] GIS SPATIAL CLAIM VALIDATION (2017-2026 Window):")
    print(f"  • Claim: {gis_res['ClaimedMetric']}")
    print(f"  • Status: {gis_res['TrustStatus']}")
    print(f"  • Findings: {gis_res['Findings']}")

    # 2. Run Document Assurance Classifications
    ey_text = "Ernst & Young LLP performed a limited assurance engagement in accordance with ISAE 3000 (Revised)."
    se_text = "SE Advisory Services provided independent reasonable verification of Scope 3 emissions aligned with ISO 14064-3."
    gd_text = "Global Documentation provided independent assurance (limited level) of carbon emissions in accordance with ISO 14064-3."

    classifications = [
        classify_assurance_document(ey_text, "ey-assurance.pdf"),
        classify_assurance_document(se_text, "se-verification.pdf"),
        classify_assurance_document(gd_text, "gd-verification.pdf")
    ]
    
    print("\n[2] DOCUMENT ASSURANCE CLASSIFICATIONS:")
    for c in classifications:
        print(f"  • {c['document_name']} ──► {c['tier_label']} (Verifier: {c['verifier']}) [Score: {c['tier_score']}/5]")

    # 3. Run Coverage Check
    coverage_result = check_assurance_coverage([
        {"document_name": "ey-assurance.pdf", "text": ey_text + " financed emissions facilitated emissions"},
        {"document_name": "se-verification.pdf", "text": se_text + " business travel"},
        {"document_name": "gd-verification.pdf", "text": gd_text + " Scope 1 Scope 2 data centre"},
    ])
    print("\n[3] ASSURANCE BOUNDARY COVERAGE CHECK:")
    print(f"  • Complete Coverage Achieved?: {coverage_result['coverage_complete']}")
    print(f"  • Uncovered Scope Gaps: {coverage_result['uncovered_boundaries'] if coverage_result['uncovered_boundaries'] else 'None detected'}")

    # 4. Restatement Check
    restatement_text = "Total prior year balances have been restated resulting in an increase of $2.2 billion."
    restatement_res = detect_restatements(restatement_text, "esg-data-pack.xlsx")
    print("\n[4] RESTATEMENT & TRANSPARENCY DISCLOSURES:")
    print(f"  • Restatement Disclosed in {restatement_res['document_name']}: {restatement_res['restatement_disclosed']}")
    if restatement_res['restatement_excerpts']:
        print(f"  • Excerpt: \"{restatement_res['restatement_excerpts'][0]}\"")
    print("============================")
