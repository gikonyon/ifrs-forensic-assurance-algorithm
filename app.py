import re
import datetime
import pandas as pd


# ---------------------------------------------------------------------------
# 1. PRIMARY DISCLOSURE INGESTION
#    (unchanged feature — confirms the uploaded report belongs to the entity
#    named on its pages; kept here so the classification steps below can call it)
# ---------------------------------------------------------------------------

def extract_entity_from_document(document_text, document_name=""):
    """
    Confirms the uploaded Primary Disclosure Report (e.g. Annual Report PDF)
    belongs to the entity named on its pages. This is the existing ingestion
    step — logic untouched in purpose, just made reusable.
    """
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
#    Fixes Gap 1 (EY mislabeled as "ISO certificate" instead of ISAE 3000
#    limited assurance) and Gap 2 (independent GHG verification statements
#    under-scored as "self-reported").
# ---------------------------------------------------------------------------

# Standard-name detection is kept STRICTLY separate from assurance-level
# detection. Matching "ISO 14064-3" requires the literal standard reference,
# never just an assurance-level phrase like "limited assurance" on its own.
# This is what fixes the original bug (EY's ISAE 3000 letter, which never
# mentions ISO 14064-3, must never be tagged as an ISO 14064-3 document).
STANDARD_NAME_PATTERNS = {
    "ISO 14064-3": r"ISO\s*14064-3",
    "ISAE 3000": r"ISAE\)?\s*3000",
    "GRI Standards": r"Global\s+Reporting\s+Initiative|\bGRI\b",
    "TCFD": r"Task\s+Force\s+on\s+Climate|\bTCFD\b",
    "SASB": r"Sustainability\s+Accounting\s+Standards\s+Board|\bSASB\b",
    "CDP": r"\bCDP\b|Carbon\s+Disclosure\s+Project",
    "GHG Protocol": r"GHG\s+Protocol|Greenhouse\s+Gas\s+Protocol",
}

# Deliberately loose on what follows "reasonable"/"limited" — real documents
# phrase this inconsistently ("reasonable level of verification", "assurance
# (limited level)", "limited assurance"), so we match on the level word plus
# an assurance-related neighbor rather than one rigid word order.
ASSURANCE_LEVEL_PATTERNS = {
    "reasonable": r"reasonable\s+(level|assurance|verification)",
    "limited": r"limited\s+(level|assurance|verification)",
}

# Standards that carry a formal assurance-level distinction (reasonable vs
# limited). Standards without one (GRI, TCFD, SASB, CDP, GHG Protocol) are
# frameworks/methodologies, not assurance engagements — they never earn an
# "assurance" tier no matter what other language appears near them.
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
    ("independent_verification", None): 3,       # standard named, level unclear
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
    """
    Detects which standard(s) an uploaded ISO certificate / audit opinion /
    verification statement actually invokes, and — separately — the
    assurance LEVEL (reasonable vs limited) that applies to that specific
    standard, rather than dumping every third-party document into one
    blanket "ISO Standard / Certificate" bucket.
    """
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
            # Only assurance-engagement standards (ISO 14064-3, ISAE 3000)
            # get credit for a reasonable/limited level; frameworks don't.
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
#    Fixes Gap 3: a data pack should not receive one blanket score when only
#    some of its metrics carry the company's own assurance marker.
# ---------------------------------------------------------------------------

def score_data_pack_metrics(dataframe, assured_marker="^"):
    """
    Scores each row of an uploaded CSV/XLSX validation file individually.
    Rows carrying the company's own assurance marker (e.g. '^' for figures
    EY put in scope) are scored as externally assured; every other row in
    the same workbook is scored as self-reported / unaudited — even though
    it sits in the same file as verified figures.
    """
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
#    Fixes Gap 4: nothing previously checked whether the combined set of
#    uploaded verification documents actually covers all expected scopes.
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
    """
    `document_texts`: list of {"document_name": ..., "text": ...} for every
    uploaded verification/assurance document. Flags any expected emissions
    boundary that none of the uploaded documents actually cover.
    """
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
#    Fixes Gap 5: prior-year restatements should be surfaced as a
#    transparency note rather than silently passed over.
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
# 6. GIS / SPATIAL CLAIM VERIFICATION — UNCHANGED FROM THE ORIGINAL ENGINE
#    Handles physical, location-bound claims (forest cover, school
#    construction). Left exactly as written; this is a separate verification
#    pathway from the document-tier scoring above, not a replacement for it.
# ---------------------------------------------------------------------------

def evaluate_esg_claim(entity_name, claim_id, category, claimed_metric,
                        claim_year, spatial_bounds, gis_observation_data):
    """
    Evaluates a corporate ESG claim against historical GIS data and independent audits.
    """
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
# 7. AGGREGATE REPORT BUILDER
#    Ties everything above to the two existing upload steps:
#      Step 1 — Primary Disclosure Ingestion (main report PDF)
#      Step 2 — Attached ISO Certificates & Tangible ESG Data (GIS/Excel)
#    The upload flow itself is unchanged; only the scoring that runs on
#    what's uploaded is replaced.
# ---------------------------------------------------------------------------

def build_verification_report(entity_name, primary_disclosure_text, primary_disclosure_name,
                                supporting_documents, data_pack_dataframes=None,
                                gis_claims=None):
    """
    supporting_documents: list of {"document_name": ..., "text": ...}
        -> ISO certificates, audit opinions, verification statements
    data_pack_dataframes: optional list of {"document_name": ..., "dataframe": pd.DataFrame}
        -> uploaded CSV/XLSX validation data
    gis_claims: optional list of kwargs dicts to pass to evaluate_esg_claim,
        for any location-bound physical claims found in the primary disclosure
    """
    ingestion_check = extract_entity_from_document(primary_disclosure_text, primary_disclosure_name)

    document_classifications = [
        classify_assurance_document(doc["text"], doc["document_name"])
        for doc in supporting_documents
    ]

    coverage = check_assurance_coverage(supporting_documents)

    all_docs_for_restatement_check = supporting_documents + [
        {"document_name": primary_disclosure_name, "text": primary_disclosure_text}
    ]
    restatement_flags = [
        r for r in (detect_restatements(d["text"], d["document_name"]) for d in all_docs_for_restatement_check)
        if r["restatement_disclosed"]
    ]

    data_pack_scores = []
    if data_pack_dataframes:
        for pack in data_pack_dataframes:
            score = score_data_pack_metrics(pack["dataframe"])
            score["document_name"] = pack["document_name"]
            data_pack_scores.append(score)

    gis_results = []
    if gis_claims:
        gis_results = [evaluate_esg_claim(**claim) for claim in gis_claims]

    all_tier_scores = [d["tier_score"] for d in document_classifications]
    max_possible = len(all_tier_scores) * 5 if all_tier_scores else 1
    aggregate_score = sum(all_tier_scores)

    return {
        "entity_evaluated": entity_name,
        "primary_disclosure_ingestion": ingestion_check,
        "document_classifications": document_classifications,
        "coverage_check": coverage,
        "restatement_disclosures": restatement_flags,
        "data_pack_metric_scores": data_pack_scores,
        "gis_claim_results": gis_results,
        "aggregate_score": f"{aggregate_score} / {max_possible}",
    }


# ---------------------------------------------------------------------------
# EXAMPLE RUN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_gis_data_1 = {'baseline_ndvi': 0.62, 'current_ndvi': 0.41}
    result_1 = evaluate_esg_claim(
        entity_name="GreenCorp Ltd",
        claim_id="CLM-2021-04",
        category="Environmental",
        claimed_metric="5,000 ha of indigenous forest restored and protected since 2017",
        claim_year=2021,
        spatial_bounds="Polygon(1.2921, 36.8219)",
        gis_observation_data=sample_gis_data_1,
    )
    print("--- GIS Spatial Claim Check (unchanged) ---")
    print(pd.DataFrame([result_1]).to_string(index=False))

    ey_text = ("Ernst & Young LLP was engaged by Standard Chartered Plc to perform a limited "
               "assurance engagement in accordance with International Standard on Assurance "
               "Engagements (ISAE) 3000 (Revised).")
    se_text = ("SE Advisory Services... provided independent third-party reasonable verification "
               "of Scope 3 emissions... aligned with the ISO 14064-3:2019 standard.")
    gd_text = ("Global Documentation... provide independent assurance (limited level) of carbon "
               "emissions... in accordance with ISO 14064-3.")

    print("\n--- Document Classification Check (fixes Gaps 1 & 2) ---")
    print(pd.DataFrame([
        classify_assurance_document(ey_text, "ey-assurance-report-sustainability.pdf"),
        classify_assurance_document(se_text, "environmental-verification-report-ea.pdf"),
        classify_assurance_document(gd_text, "environmental-verification-report-gd.pdf"),
    ])[["document_name", "detected_standards", "tier_label", "tier_score", "verifier"]].to_string(index=False))

    print("\n--- Coverage Check (fixes Gap 4) ---")
    coverage_result = check_assurance_coverage([
        {"document_name": "ey-assurance-report-sustainability.pdf", "text": ey_text + " financed emissions facilitated emissions"},
        {"document_name": "environmental-verification-report-ea.pdf", "text": se_text + " business travel"},
        {"document_name": "environmental-verification-report-gd.pdf", "text": gd_text + " Scope 1 Scope 2 data centre"},
    ])
    print(coverage_result)

    print("\n--- Restatement Detection (fixes Gap 5) ---")
    restatement_text = "Total prior year balances have been restated resulting in an increase of $2.2 billion."
    print(detect_restatements(restatement_text, "esg-data-pack.xlsx"))
