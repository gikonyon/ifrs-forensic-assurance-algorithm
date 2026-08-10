import os
import json
import csv
import re
import math
import hashlib
import io
from html.parser import HTMLParser
from typing import Dict, List, Any, Optional

import pypdf
import docx
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# =====================================================================
# 1. MULTI-FORMAT EVIDENCE PARSER (HTML, PDF, DOCX)
# =====================================================================

class DisclosureHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_content = []

    def handle_data(self, data: str):
        cleaned = data.strip()
        if cleaned:
            self.text_content.append(cleaned)

    def get_text(self) -> str:
        return " ".join(self.text_content)


class DocumentExtractor:
    """Extracts raw text content from HTML, PDF, and DOCX files."""
    
    @staticmethod
    def extract_text_from_html(raw_bytes: bytes) -> str:
        html_str = raw_bytes.decode("utf-8", errors="ignore")
        parser = DisclosureHTMLParser()
        parser.feed(html_str)
        return parser.get_text()

    @staticmethod
    def extract_text_from_pdf(raw_bytes: bytes) -> str:
        pdf_file = io.BytesIO(raw_bytes)
        reader = pypdf.PdfReader(pdf_file)
        text = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text.append(extracted)
        return " ".join(text)

    @staticmethod
    def extract_text_from_docx(raw_bytes: bytes) -> str:
        docx_file = io.BytesIO(raw_bytes)
        doc = docx.Document(docx_file)
        text = [para.text for para in doc.paragraphs if para.text.strip()]
        return " ".join(text)

    @classmethod
    def process_file(cls, raw_bytes: bytes, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        if ext in [".html", ".htm"]:
            return cls.extract_text_from_html(raw_bytes)
        elif ext == ".pdf":
            return cls.extract_text_from_pdf(raw_bytes)
        elif ext in [".docx", ".doc"]:
            return cls.extract_text_from_docx(raw_bytes)
        else:
            return raw_bytes.decode("utf-8", errors="ignore")


class DisclosureParser:
    """Parses extracted text to pull IFRS S1 and S2 metrics using Regex."""
    
    def parse_text(self, text: str) -> Dict[str, Any]:
        extracted_data = {
            "entity_name": "Unknown Entity",
            "reporting_period": "2025/2026",
            "metrics": {},
            "governance": {}
        }

        # Entity Name
        entity_match = re.search(r"Company Name:\s*([A-Za-z0-9\s&]+)", text, re.I)
        if entity_match:
            extracted_data["entity_name"] = entity_match.group(1).strip()

        # IFRS S2 Climate Variables
        s1_match = re.search(r"Scope\s*1\s*(?:Emissions)?:\s*([\d,]+(?:\.\d+)?)", text, re.I)
        s2_match = re.search(r"Scope\s*2\s*(?:Emissions)?:\s*([\d,]+(?:\.\d+)?)", text, re.I)
        output_match = re.search(r"Total\s*Output:\s*([\d,]+(?:\.\d+)?)", text, re.I)

        if s1_match:
            extracted_data["metrics"]["scope_1"] = float(s1_match.group(1).replace(",", ""))
        if s2_match:
            extracted_data["metrics"]["scope_2"] = float(s2_match.group(1).replace(",", ""))
        if output_match:
            extracted_data["metrics"]["total_output"] = float(output_match.group(1).replace(",", ""))

        # IFRS S1 Governance Variables
        male_match = re.search(r"Male\s*Board\s*Members:\s*(\d+)", text, re.I)
        female_match = re.search(r"Female\s*Board\s*Members:\s*(\d+)", text, re.I)

        if male_match:
            extracted_data["governance"]["male_count"] = int(male_match.group(1))
        if female_match:
            extracted_data["governance"]["female_count"] = int(female_match.group(1))

        return extracted_data


# =====================================================================
# 2. FORENSIC VERIFICATION ENGINE
# =====================================================================

class IFRSForensicEngine:
    def __init__(self, tolerance_threshold: float = 0.02):
        self.tolerance_threshold = tolerance_threshold

    def calculate_hhi(self, shares: List[float]) -> float:
        total = sum(shares)
        if total == 0:
            return 0.0
        normalized = [s / total for s in shares]
        return sum(s ** 2 for s in normalized)

    def calculate_ghg_intensity(self, scope_1: float, scope_2: float, total_output: float) -> float:
        if total_output <= 0:
            return 0.0
        return (scope_1 + scope_2) / total_output

    def assess_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
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

    def verify_disclosure(self, parsed_data: Dict[str, Any], raw_bytes: bytes) -> Dict[str, Any]:
        metrics = parsed_data.get("metrics", {})
        gov = parsed_data.get("governance", {})

        s1 = metrics.get("scope_1", 0.0)
        s2 = metrics.get("scope_2", 0.0)
        output = metrics.get("total_output", 1.0)

        calc_intensity = self.calculate_ghg_intensity(s1, s2, output)

        board_total = gov.get("male_count", 0) + gov.get("female_count", 0)
        board_shares = [gov.get("male_count", 0), gov.get("female_count", 0)] if board_total > 0 else [1]
        hhi_index = self.calculate_hhi(board_shares)

        file_hash = hashlib.sha256(raw_bytes).hexdigest()

        exceptions = []
        if output <= 0:
            exceptions.append("INVALID_OUTPUT_DENOMINATOR")
        if s1 == 0.0 and s2 == 0.0:
            exceptions.append("ZERO_REPORTED_EMISSIONS_ALERT")

        dqs = self.assess_data_quality(parsed_data)
        risk_state = "ALPHA" if len(exceptions) == 0 and dqs["score"] > 0.8 else "OMEGA"

        return {
            "entity_name": parsed_data.get("entity_name"),
            "reporting_period": parsed_data.get("reporting_period"),
            "data_lineage_sha256": file_hash,
            "recalculated_ghg_intensity": round(calc_intensity, 4),
            "governance_hhi": round(hhi_index, 4),
            "data_quality": dqs,
            "exceptions_detected": exceptions,
            "assurance_risk_state": risk_state
        }


# =====================================================================
# 3. REPORTLAB PDF REPORT GENERATOR
# =====================================================================

def generate_pdf_report(results: Dict[str, Any]) -> bytes:
    """Generates an IFRS Forensic Assurance Report as a PDF byte stream."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=12
    )
    story.append(Paragraph("IFRS Forensic Assurance Verification Report", title_style))
    story.append(Paragraph("<b>Standard Alignment:</b> IFRS S1 (Governance) & IFRS S2 (Climate)", styles['Normal']))
    story.append(Spacer(1, 12))

    data = [
        ["Metric / Indicator", "Forensic Result"],
        ["Entity Name", str(results.get("entity_name", "Unknown"))],
        ["Reporting Period", str(results.get("reporting_period", "N/A"))],
        ["Assurance Risk State", str(results.get("assurance_risk_state", "N/A"))],
        ["Recalculated GHG Intensity", f"{results.get('recalculated_ghg_intensity', 0):.4f}"],
        ["Governance HHI", f"{results.get('governance_hhi', 0):.4f}"],
        ["Data Quality Score (DQS)", f"{results.get('data_quality', {}).get('score', 0)} ({results.get('data_quality', {}).get('tier', 'N/A')})"],
        ["Exceptions Detected", ", ".join(results.get("exceptions_detected", [])) or "None"],
        ["SHA-256 Evidence Hash", str(results.get("data_lineage_sha256", "N/A"))[:32] + "..."]
    ]

    t = Table(data, colWidths=[200, 340])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>Notice:</b> This document is an automated research prototype report generated for transaction-level disclosure verification.", styles['Italic']))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
