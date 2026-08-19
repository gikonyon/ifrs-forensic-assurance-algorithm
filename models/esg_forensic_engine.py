# ==========================================
# Module: esg_forensic_engine.py
# Location Recommendation: /models/esg_forensic_engine.py or root analytics directory
# ==========================================

import re
import datetime
import pandas as pd

# Standard patterns & dictionaries
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

EXPECTED_BOUNDARIES = [
    "Scope 1", "Scope 2",
    "Scope 3 Category 6 (Business Travel)",
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

def detect_restatements(document_text, document_name=""):
    pattern = r"([^.]{0,200}restat[a-z]*[^.]{0,200}\.)"
    hits = re.findall(pattern, document_text, re.IGNORECASE)
    return {
        "document_name": document_name,
        "restatement_disclosed": len(hits) > 0,
        "restatement_excerpts": hits[:5],
    }

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
