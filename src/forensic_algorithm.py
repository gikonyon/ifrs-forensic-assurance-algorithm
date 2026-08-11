import os
import json
import re
import hashlib
import io
from html.parser import HTMLParser
from typing import Dict, List, Any, Optional

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# =====================================================================
# 1. MULTI-FORMAT DOCUMENT EXTRACTOR & SMART COVER PAGE PARSER
# =====================================================================

class DisclosureHTMLParser(HTMLParser):
    """Parses HTML markup and extracts plain text content."""
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
    """Extracts raw text content from PDF, DOCX, HTML, and plain text files."""
    
    @staticmethod
    def extract_text_from_pdf(raw_bytes: bytes) -> str:
        if pypdf is None:
            return ""
        pdf_file = io.BytesIO(raw_bytes)
        reader = pypdf.PdfReader(pdf_file)
        text = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text.append(extracted)
        return "\n".join(text)

    @classmethod
    def process_file(cls, raw_bytes: bytes, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".pdf":
            return cls.extract_text_from_pdf(raw_bytes)
        elif ext in [".docx", ".doc"]:
            if docx is None:
                return ""
            doc = docx.Document(io.BytesIO(raw_bytes))
            return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        elif ext in [".html", ".htm"]:
            parser = DisclosureHTMLParser()
            parser.feed(raw_bytes.decode("utf-8", errors="ignore"))
            return parser.get_text()
        else:
            return raw_bytes.decode("utf-8", errors="ignore")


# =====================================================================
# 2. ENHANCED DISCLOSURE PARSER (NCBA & FINANCIAL DISCLOSURES)
# =====================================================================

class EnhancedDisclosureParser:
    """Parses disclosure text for entities, Scope 1/2 emissions, greenwashing risk, and community impact."""
    
    GREENWASH_KEYWORDS = [
        "net zero", "carbon neutral", "eco friendly", "sustainable future",
        "green initiative", "climate champion", "environmentally conscious"
    ]

    COMMUNITY_BENEFIT_KEYWORDS = [
        "water source", "water point", "ict training", "hospital upgrade",
        "skills development", "regional infrastructure", "local community",
        "scholarships", "mentorship", "financial literacy", "trees planted", "tree planting"
    ]

    def parse_text(self, text: str) -> Dict[str, Any]:
        data = {
            "entity_name": "Unknown Entity",
            "reporting_period": "2025/2026",
            "metrics": {},
            "governance": {},
            "greenwash_analysis": {},
            "community_impact": {}
        }

        # 1. Smart Entity Extraction (First 600 characters / Cover page area)
        cover_text = text[:600]
        if "NCBA" in cover_text:
            data["entity_name"] = "NCBA Bank Kenya PLC"
        else:
            entity_patterns = [
                r"DISCLOSURE:\s*([A-Za-z0-9\s]+)",
                r"([A-Za-z0-9\s]+)\s+PLC",
                r"([A-Za-z0-9\s]+)\s+BANK",
                r"(?:Company Name|Entity):\s*([A-Za-z0-9\s&]+)"
            ]
            for pat in entity_patterns:
                match = re.search(pat, cover_text, re.I)
                if match:
                    data["entity_name"] = match.group(1).strip()
                    break

        # 2. Scope 1 and Scope 2 Emissions Parsing
        s1_match = re.search(r"Scope\s*1\s*(?:greenhouse\s*gas\s*emissions|emissions)?\s*(?:\(tCO2e\))?[\s:]*([\d,]+(?:\.\d+)?)", text, re.I)
        s2_match = re.search(r"Scope\s*2\s*(?:greenhouse\s*gas\s*emissions|emissions)?\s*(?:\(tCO2e\))?[\s:]*([\d,]+(?:\.\d+)?)", text, re.I)
        
        if s1_match:
            data["metrics"]["scope_1"] = float(s1_match.group(1).replace(",", ""))
        if s2_match:
            data["metrics"]["scope_2"] = float(s2_match.group(1).replace(",", ""))

        output_match = re.search(r"Total\s*Output:\s*([\d,]+(?:\.\d+)?)", text, re.I)
        if output_match:
            data["metrics"]["total_output"] = float(output_match.group(1).replace(",", ""))
        else:
            data["metrics"]["total_output"] = 1.0

        # 3. Board Diversity & Governance Parsing
        female_board_match = re.search(r"Board\s*gender\s*diversity\s*\(?Women\s*in\s*leadership\)?[\s:]*(\d+)%", text, re.I)
        if female_board_match:
            female_pct = float(female_board_match.group(1))
            data["governance"]["female_pct"] = female_pct
            data["governance"]["male_pct"] = 100.0 - female_pct

        # 4. Greenwashing Risk Analysis
        text_lower = text.lower()
        buzzword_count = sum(text_lower.count(kw) for kw in self.GREENWASH_KEYWORDS)
        data["greenwash_analysis"]["narrative_buzzword_count"] = buzzword_count
        
        has_metrics = "scope_1" in data["metrics"] or "scope_2" in data["metrics"]
        if buzzword_count > 10 and not has_metrics:
            data["greenwash_analysis"]["risk_level"] = "HIGH_GREENWASHING_RISK"
        else:
            data["greenwash_analysis"]["risk_level"] = "LOW_OR_VERIFIED"

        # 5. Local Community Impact Indicators
        community_hits = [kw for kw in self.COMMUNITY_BENEFIT_KEYWORDS if kw in text_lower]
        data["community_impact"]["verified_initiatives"] = list(set(community_hits))
        data["community_impact"]["score"] = min(10.0, len(set(community_hits)) * 1.5)

        return data


# =====================================================================
# 3. FORENSIC VERIFICATION ENGINE & 1-9 INDEX SYSTEM
# =====================================================================

class IFRSForensicEngine:
    """Calculates standardized 1–9 ESG Index scores and generates forensic audit results."""

    def verify_disclosure(self, parsed_data: Dict[str, Any], raw_bytes: bytes) -> Dict[str, Any]:
        metrics = parsed_data.get("metrics", {})
        gov = parsed_data.get("governance", {})
        impact = parsed_data.get("community_impact", {})

        s1 = metrics.get("scope_1", 0.0)
        s2 = metrics.get("scope_2", 0.0)
        output = metrics.get("total_output", 1.0)

        calc_intensity = (s1 + s2) / output if output > 0 else 0.0

        # Calculate Standardized 1–9 ESG Index Score
        index_score = 1.0  # Baseline
        
        if s1 > 0: index_score += 1.5
        if s2 > 0: index_score += 1.5
        if "female_pct" in gov: index_score += 2.0
        
        impact_score = impact.get("score", 0.0)
        index_score += min(2.0, impact_score / 5.0)

        if parsed_data.get("greenwash_analysis", {}).get("risk_level") == "HIGH_GREENWASHING_RISK":
            index_score = max(1.0, index_score - 2.0)

        final_index = round(min(9.0, max(1.0, index_score)), 1)

        # Performance Tier Categorization
        if final_index >= 8.0:
            rating_label = "EXCELLENT (GOOD)"
        elif final_index >= 6.0:
            rating_label = "GOOD (VERIFIED)"
        elif final_index >= 4.0:
            rating_label = "MODERATE (CONTROLLED)"
        else:
            rating_label = "POOR / HIGH RISK (BAD)"

        exceptions = []
        if s1 == 0.0 and s2 == 0.0:
            exceptions.append("ZERO_REPORTED_EMISSIONS_ALERT")

        file_hash = hashlib.sha256(raw_bytes).hexdigest()

        return {
            "entity_name": parsed_data.get("entity_name"),
            "reporting_period": parsed_data.get("reporting_period"),
            "data_lineage_sha256": file_hash,
            "esg_index_score": final_index,
            "esg_rating_label": rating_label,
            "recalculated_ghg_intensity": round(calc_intensity, 2),
            "scope_1_tco2e": s1,
            "scope_2_tco2e": s2,
            "greenwash_analysis": parsed_data.get("greenwash_analysis", {}),
            "community_impact": parsed_data.get("community_impact", {}),
            "exceptions_detected": exceptions,
            "assurance_risk_state": "ALPHA" if final_index >= 6.0 else "OMEGA"
        }


# =====================================================================
# 4. REPORTLAB PDF REPORT GENERATOR (WITH FOOTER VERIFICATION HASH)
# =====================================================================

def generate_pdf_report(results: Dict[str, Any], multi_results: Optional[Dict[str, Any]] = None) -> bytes:
    """Generates an executive PDF report with SHA-256 audit fingerprint in the footer."""
    if not REPORTLAB_AVAILABLE:
        return b"%PDF-1.4 empty placeholder"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ReportTitle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1E3A8A'), spaceAfter=10
    )
    story.append(Paragraph("IFRS / NSE ESG Forensic Assurance Audit", title_style))
    story.append(Paragraph("<b>Standard Alignment:</b> IFRS S1, IFRS S2, NSE ESG, ISO 14064, UNDP SDG 16", styles['Normal']))
    story.append(Spacer(1, 12))

    comp_score_str = f"{multi_results.get('composite_score_100', 0)} / 100 ({multi_results.get('maturity_stage', 'N/A')})" if multi_results else "N/A"

    data = [
        ["Audit Parameter", "Forensic Result"],
        ["Entity Name", str(results.get("entity_name", "Unknown"))],
        ["ESG Index Score (1-9)", f"{results.get('esg_index_score', 1.0)} / 9.0 ({results.get('esg_rating_label', 'N/A')})"],
        ["Multi-Framework Composite Score", comp_score_str],
        ["Assurance Risk State", str(results.get("assurance_risk_state", "N/A"))],
        ["Scope 1 Emissions", f"{results.get('scope_1_tco2e', 0):,.2f} tCO2e"],
        ["Scope 2 Emissions", f"{results.get('scope_2_tco2e', 0):,.2f} tCO2e"],
        ["Greenwashing Risk", str(results.get("greenwash_analysis", {}).get("risk_level", "VERIFIED"))],
        ["Community Impact Initiatives", ", ".join(results.get("community_impact", {}).get("verified_initiatives", [])) or "None"],
    ]

    t = Table(data, colWidths=[200, 340])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    footer_style = ParagraphStyle('FooterStyle', parent=styles['Italic'], fontSize=8, textColor=colors.HexColor('#64748B'))
    story.append(Paragraph(f"<b>Document Verification Fingerprint (SHA-256):</b> {results.get('data_lineage_sha256', 'N/A')}", footer_style))
    story.append(Paragraph("Automated forensic assurance report evaluating corporate disclosure data, regional impact, and greenwashing risks.", footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
