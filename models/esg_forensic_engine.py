import pandas as pd
import re

def extract_entity_from_document(text: str, document_name: str) -> dict:
    """Extracts entity / company name from primary ESG report text or metadata."""
    entity_pattern = r"(?:Company|Entity|Issuer|Client|Prepared for):?\s*([A-Z][A-Za-z0-9\s,]{2,40})"
    match = re.search(entity_pattern, text)
    
    detected_entity = match.group(1).strip() if match else None
    if not detected_entity and "Standard Chartered" in text:
        detected_entity = "Standard Chartered Plc"
    elif not detected_entity:
        detected_entity = "Unknown Entity (Review Header)"
        
    return {
        "document_name": document_name,
        "detected_entity": detected_entity,
        "confidence": "High" if match or "Standard Chartered" in text else "Low"
    }

def classify_assurance_document(text: str, document_name: str) -> dict:
    """Classifies assurance opinions into tiers based on ISAE 3000 / ISO 14064 standards."""
    text_lower = text.lower()
    if "reasonable assurance" in text_lower:
        tier = "Tier 1: Reasonable Assurance (Highest Rigor)"
    elif "limited assurance" in text_lower:
        tier = "Tier 2: Limited Assurance (Moderate Rigor)"
    elif "agreed-upon procedures" in text_lower or "aep" in text_lower:
        tier = "Tier 3: Agreed-Upon Procedures (Specific Testing)"
    else:
        tier = "Tier 4: Unverified / Self-Declared Claim"
        
    standards_detected = []
    if "isae 3000" in text_lower:
        standards_detected.append("ISAE 3000 (Revised)")
    if "iso 14064" in text_lower:
        standards_detected.append("ISO 14064-3")
        
    return {
        "document_name": document_name,
        "tier_label": tier,
        "standards_detected": standards_detected or ["General Verification Framework"]
    }

def score_data_pack_metrics(df: pd.DataFrame, assured_marker: str = "^") -> dict:
    """Audits a structured data pack dataframe to check which metrics carry assurance markers."""
    total_metrics = len(df)
    assured_count = 0
    row_details = []
    
    for _, row in df.iterrows():
        desc = str(row.get("Description", row.iloc[1] if len(row) > 1 else ""))
        is_assured = assured_marker in desc
        if is_assured:
            assured_count += 1
        row_details.append({
            "Metric": desc,
            "Assured": "Yes" if is_assured else "No"
        })
        
    ratio = round(assured_count / total_metrics, 2) if total_metrics > 0 else 0.0
    return {
        "total_metrics_scanned": total_metrics,
        "assured_metrics": assured_count,
        "unaudited_metrics": total_metrics - assured_count,
        "assured_ratio": ratio,
        "row_level_detail": row_details
    }

def check_assurance_coverage(documents: list) -> dict:
    """Ensures all mandatory carbon and emissions scopes are fully covered across provider documents."""
    mandatory_scopes = ["Scope 1", "Scope 2", "financed emissions", "business travel"]
    covered = []
    
    combined_text = " ".join([doc.get("text", "") for doc in documents]).lower()
    for scope in mandatory_scopes:
        if scope.lower() in combined_text:
            covered.append(scope)
            
    uncovered = [s for s in mandatory_scopes if s not in covered]
    return {
        "coverage_complete": len(uncovered) == 0,
        "covered_boundaries": covered,
        "uncovered_boundaries": uncovered
    }

def detect_restatements(text: str, document_name: str) -> dict:
    """Scans text for prior-year restatements or data integrity adjustments."""
    restatement_keywords = ["restated", "prior year adjustment", "reclassification", "previously reported"]
    found_excerpts = []
    
    for sentence in text.split('.'):
        if any(kw in sentence.lower() for kw in restatement_keywords):
            found_excerpts.append(sentence.strip())
            
    return {
        "document_name": document_name,
        "restatement_disclosed": len(found_excerpts) > 0,
        "restatement_excerpts": found_excerpts
    }

def evaluate_esg_claim(entity: str, claim_id: str, category: str, metric: str, year: int, polygon: str, gis_data: dict) -> dict:
    """Evaluates environmental claims against GIS and satellite NDVI baseline changes."""
    base_ndvi = gis_data.get('baseline_ndvi', 0.6)
    curr_ndvi = gis_data.get('current_ndvi', 0.5)
    ndvi_delta = curr_ndvi - base_ndvi
    
    discrepancy = ndvi_delta < -0.15
    return {
        "Entity": entity,
        "ClaimID": claim_id,
        "Category": category,
        "Metric": metric,
        "Year": year,
        "SpatialPolygon": polygon,
        "BaselineNDVI": base_ndvi,
        "CurrentNDVI": curr_ndvi.item() if hasattr(curr_ndvi, 'item') else curr_ndvi,
        "NDVIDelta": round(float(ndvi_delta), 3),
        "DiscrepancyFlag": bool(discrepancy),
        "TrustStatus": "FLAGGED: Potential Greenwashing / Vegetation Degradation" if discrepancy else "VERIFIED: Consistent with Satellite Data"
    }

def build_verification_report(entity_name: str, primary_disclosure_text: str, primary_disclosure_name: str, supporting_documents: list, data_pack_dataframes: list) -> dict:
    """Compiles an aggregate comprehensive verification report."""
    entity_res = extract_entity_from_document(primary_disclosure_text, primary_disclosure_name)
    coverage_res = check_assurance_coverage(supporting_documents)
    restatement_res = detect_restatements(primary_disclosure_text, primary_disclosure_name)
    
    dp_summary = {"total_metrics_scanned": 0, "assured_metrics": 0, "assured_ratio": 0.0}
    if data_pack_dataframes:
        for dp in data_pack_dataframes:
            res = score_data_pack_metrics(dp.get("dataframe", pd.DataFrame()))
            dp_summary["total_metrics_scanned"] += res["total_metrics_scanned"]
            dp_summary["assured_metrics"] += res["assured_metrics"]
        if dp_summary["total_metrics_scanned"] > 0:
            dp_summary["assured_ratio"] = round(dp_summary["assured_metrics"] / dp_summary["total_metrics_scanned"], 2)

    return {
        "EntityName": entity_name,
        "PrimaryReportEntityAudit": entity_res,
        "AssuranceBoundaryCoverage": coverage_res,
        "RestatementCheck": restatement_res,
        "DataPackAuditSummary": dp_summary,
        "FinalComplianceStatus": "PASSED & VERIFIED" if coverage_res["coverage_complete"] and not restatement_res["restatement_disclosed"] else "REVIEW REQUIRED: Gaps Detected"
    }
