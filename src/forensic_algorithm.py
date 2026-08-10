import os
import json
import csv
import re
import math
import hashlib
from html.parser import HTMLParser
from typing import Dict, List, Any, Optional


# =====================================================================
# 1. HTML EVIDENCE PARSER
# =====================================================================

class DisclosureHTMLParser(HTMLParser):
    """
    Parses corporate HTML disclosures to extract key ESG variables,
    lineage payloads, and metadata for IFRS S1/S2 analysis.
    """
    def __init__(self):
        super().__init__()
        self.text_content = []
        self.extracted_data = {
            "entity_name": "Unknown Entity",
            "reporting_period": "2025/2026",
            "metrics": {},
            "governance": {}
        }

    def handle_data(self, data: str):
        cleaned = data.strip()
        if cleaned:
            self.text_content.append(cleaned)

    def extract_variables(self, html_content: str) -> Dict[str, Any]:
        self.feed(html_content)
        full_text = " ".join(self.text_content)

        # Regex patterns to extract variables directly from HTML text
        entity_match = re.search(r"Company Name:\s*([A-Za-z0-9\s&]+)", full_text, re.I)
        if entity_match:
            self.extracted_data["entity_name"] = entity_match.group(1).strip()

        # IFRS S2 Climate Variables
        s1_match = re.search(r"Scope\s*1\s*(?:Emissions)?:\s*([\d,]+(?:\.\d+)?)", full_text, re.I)
        s2_match = re.search(r"Scope\s*2\s*(?:Emissions)?:\s*([\d,]+(?:\.\d+)?)", full_text, re.I)
        output_match = re.search(r"Total\s*Output:\s*([\d,]+(?:\.\d+)?)", full_text, re.I)

        if s1_match:
            self.extracted_data["metrics"]["scope_1"] = float(s1_match.group(1).replace(",", ""))
        if s2_match:
            self.extracted_data["metrics"]["scope_2"] = float(s2_match.group(1).replace(",", ""))
        if output_match:
            self.extracted_data["metrics"]["total_output"] = float(output_match.group(1).replace(",", ""))

        # IFRS S1 Governance Variables
        male_match = re.search(r"Male\s*Board\s*Members:\s*(\d+)", full_text, re.I)
        female_match = re.search(r"Female\s*Board\s*Members:\s*(\d+)", full_text, re.I)

        if male_match:
            self.extracted_data["governance"]["male_count"] = int(male_match.group(1))
        if female_match:
            self.extracted_data["governance"]["female_count"] = int(female_match.group(1))

        return self.extracted_data


# =====================================================================
# 2. FORENSIC VERIFICATION ENGINE
# =====================================================================

class IFRSForensicEngine:
    def __init__(self, tolerance_threshold: float = 0.02):
        self.tolerance_threshold = tolerance_threshold

    def calculate_hhi(self, shares: List[float]) -> float:
        """Calculates Herfindahl-Hirschman Index (HHI) for governance concentration."""
        total = sum(shares)
        if total == 0:
            return 0.0
        normalized = [s / total for s in shares]
        return sum(s ** 2 for s in normalized)

    def calculate_ghg_intensity(self, scope_1: float, scope_2: float, total_output: float) -> float:
        """Calculates GHG Intensity: Ic = (Scope 1 + Scope 2) / Total Output."""
        if total_output <= 0:
            return 0.0
        return (scope_1 + scope_2) / total_output

    def assess_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates 5-tier Data Quality Score (DQS)."""
        metrics = data.get("metrics", {})
        has_s1 = "scope_1" in metrics
        has_s2 = "scope_2" in metrics
        has_output = "total_output" in metrics

        score = 0.0
        if has_s1 and has_s2: 
            score += 0.4
        if has_output: 
            score += 0.3
        if len(data.get("governance", {})) > 0: 
            score += 0.3

        if score >= 0.9: 
            classification = "ASSURANCE_READY"
        elif score >= 0.7: 
            classification = "VERIFIED"
        elif score >= 0.5: 
            classification = "CONTROLLED"
        elif score >= 0.3: 
            classification = "DEVELOPING"
        else: 
            classification = "MINIMAL"

        return {"score": round(score, 2), "tier": classification}

    def verify_disclosure(self, parsed_data: Dict[str, Any], raw_html: str) -> Dict[str, Any]:
        """Runs complete forensic verification, recalculations, and exception logging."""
        metrics = parsed_data.get("metrics", {})
        gov = parsed_data.get("governance", {})

        s1 = metrics.get("scope_1", 0.0)
        s2 = metrics.get("scope_2", 0.0)
        output = metrics.get("total_output", 1.0)

        # Mathematical Recalculations
        calc_intensity = self.calculate_ghg_intensity(s1, s2, output)

        board_total = gov.get("male_count", 0) + gov.get("female_count", 0)
        board_shares = [gov.get("male_count", 0), gov.get("female_count", 0)] if board_total > 0 else [1]
        hhi_index = self.calculate_hhi(board_shares)

        # Evidence Lineage Hash
        html_hash = hashlib.sha256(raw_html.encode('utf-8')).hexdigest()

        # Exception Detection
        exceptions = []
        if output <= 0:
            exceptions.append("INVALID_OUTPUT_DENOMINATOR")
        if s1 == 0.0 and s2 == 0.0:
            exceptions.append("ZERO_REPORTED_EMISSIONS_ALERT")

        # Risk Classification State
        dqs = self.assess_data_quality(parsed_data)
        risk_state = "ALPHA" if len(exceptions) == 0 and dqs["score"] > 0.8 else "OMEGA"

        return {
            "entity_name": parsed_data.get("entity_name"),
            "reporting_period": parsed_data.get("reporting_period"),
            "data_lineage_sha256": html_hash,
            "recalculated_ghg_intensity": round(calc_intensity, 4),
            "governance_hhi": round(hhi_index, 4),
            "data_quality": dqs,
            "exceptions_detected": exceptions,
            "assurance_risk_state": risk_state
        }


# =====================================================================
# 3. LOCAL PIPELINE RUNNER
# =====================================================================

def run_pipeline(input_dir: str = "data/raw_html", output_dir: str = "data/processed"):
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(input_dir, exist_ok=True)

    engine = IFRSForensicEngine()
    reports = []
    audit_logs = []

    for file_name in os.listdir(input_dir):
        if file_name.endswith(".html") or file_name.endswith(".htm"):
            file_path = os.path.join(input_dir, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            parser = DisclosureHTMLParser()
            parsed_data = parser.extract_variables(html_content)
            verification_result = engine.verify_disclosure(parsed_data, html_content)
            
            reports.append(verification_result)
            audit_logs.append({
                "file": file_name,
                "entity": verification_result["entity_name"],
                "sha256": verification_result["data_lineage_sha256"],
                "intensity": verification_result["recalculated_ghg_intensity"],
                "hhi": verification_result["governance_hhi"],
                "risk_state": verification_result["assurance_risk_state"]
            })

    json_path = os.path.join(output_dir, "diagnostic_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2)

    csv_path = os.path.join(output_dir, "verification_audit_log.csv")
    if audit_logs:
        keys = audit_logs[0].keys()
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(audit_logs)

    print(f"[+] Processing Complete. Analyzed {len(reports)} corporate report(s).")

if __name__ == "__main__":
    run_pipeline()
