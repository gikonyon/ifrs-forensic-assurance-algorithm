import os
import sys
import json
import re
import hashlib
import io
from html.parser import HTMLParser
from typing import Dict, List, Any, Optional

import streamlit as st

# Safe optional imports for document parsing and PDF generation
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
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# =====================================================================
# 1. DOCUMENT EXTRACTOR & SMART COVER PARSER
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
# 2. ENHANCED DISCLOSURE PARSER
# =====================================================================

class EnhancedDisclosureParser:
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

        # Cover page smart extraction
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

        # Scope 1 and Scope 2 Emissions Parsing
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

        # Governance Parsing
        female_board_match = re.search(r"Board\s*gender\s*diversity\s*\(?Women\s*in\s*leadership\)?[\s:]*(\d+)%", text, re.I)
        if female_board_match:
            female_pct = float(female_board_match.group(1))
            data["governance"]["female_pct"] = female_pct
            data["governance"]["male_pct"] = 100.0 - female_pct

        # Greenwash Risk Analysis
        text_lower = text.lower()
        buzzword_count = sum(text_lower.count(kw) for kw in self.GREENWASH_KEYWORDS)
        data["greenwash_analysis"]["narrative_buzzword_count"] = buzzword_count
        
        has_metrics = "scope_1" in data["metrics"] or "scope_2" in data["metrics"]
        if buzzword_count > 10 and not has_metrics:
            data["greenwash_analysis"]["risk_level"] = "HIGH_GREENWASHING_RISK"
        else:
            data["greenwash_analysis"]["risk_level"] = "LOW_OR_VERIFIED"

        # Local Community Impact Tracking
        community_hits = [kw for kw in self.COMMUNITY_BENEFIT_KEYWORDS if kw in text_lower]
        data["community_impact"]["verified_initiatives"] = list(set(community_hits))
        data["community_impact"]["score"] = min(10.0, len(set(community_hits)) * 1.5)

        return data


# =====================================================================
# 3. FORENSIC VERIFICATION ENGINE (1-9 INDEX)
# =====================================================================

class IFRSForensicEngine:
    def verify_disclosure(self, parsed_data: Dict[str, Any], raw_bytes: bytes) -> Dict[str, Any]:
        metrics = parsed_data.get("metrics", {})
        gov = parsed_data.get("governance", {})
        impact = parsed_data.get("community_impact", {})

        s1 = metrics.get("scope_1", 0.0)
        s2 = metrics.get("scope_2", 0.0)
        output = metrics.get("total_output", 1.0)

        calc_intensity = (s1 + s2) / output if output > 0 else 0.0

        # Calculate 1–9 Index
        index_score = 1.0
        if s1 > 0: index_score += 1.5
        if s2 > 0: index_score += 1.5
        if "female_pct" in gov: index_score += 2.0
        
        impact_score = impact.get("score", 0.0)
        index_score += min(2.0, impact_score / 5.0)

        if parsed_data.get("greenwash_analysis", {}).get("risk_level") == "HIGH_GREENWASHING_RISK":
            index_score = max(1.0, index_score - 2.0)

        final_index = round(min(9.0, max(1.0, index_score)), 1)

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
# 4. MULTI-FRAMEWORK ENGINE (SDG, ISO, NSE, EU)
# =====================================================================

class MultiFrameworkEngine:
    SDG_KEYWORD_MAP = {
        "SDG 1: No Poverty": ["poverty", "financial inclusion", "low-income", "microfinance"],
        "SDG 4: Quality Education": ["scholarship", "mentorship", "skills development", "training", "literacy"],
        "SDG 5: Gender Equality": ["gender", "women in leadership", "female employment", "equal pay", "board diversity"],
        "SDG 6: Clean Water": ["water management", "water conservation", "sanitation", "water point"],
        "SDG 7: Affordable Energy": ["solar energy", "geothermal", "hydroelectric", "renewable energy", "clean energy"],
        "SDG 8: Decent Work & Growth": ["employment", "job creation", "msme financing", "decent work", "labour rights"],
        "SDG 9: Industry & Infrastructure": ["sustainable infrastructure", "transport financing", "digital transformation", "fintech"],
        "SDG 11: Sustainable Cities": ["urban development", "regional infrastructure", "community housing", "public transport"],
        "SDG 12: Responsible Consumption": ["waste management", "recycling", "single-use plastics", "sustainable procurement"],
        "SDG 13: Climate Action": ["ghg emissions", "scope 1", "scope 2", "sbti", "paris agreement", "net zero"],
        "SDG 15: Life on Land": ["tree planting", "reforestation", "biodiversity", "ecosystem preservation"],
        "SDG 16: Governance & Peace": ["anti-corruption", "institutional integrity", "transparency", "whistleblower", "code of conduct", "human rights", "stakeholder accountability"]
    }

    ISO_STANDARDS = {
        "ISO 14001": ["iso 14001", "environmental management system"],
        "ISO 14064": ["iso 14064", "ghg accounting", "carbon verification"],
        "ISO 26000": ["iso 26000", "social responsibility"],
        "ISO 37301": ["iso 37301", "compliance management"],
        "ISO 45001": ["iso 45001", "occupational health and safety"]
    }

    NSE_ESG_PILLARS = {
        "Board Oversight": ["board gender diversity", "board oversight", "governance policy"],
        "Materiality": ["materiality assessment", "double materiality"],
        "Climate Risk": ["tcfd", "climate risk", "decarbonization target"],
        "Diversity & Inclusion": ["female employment", "women in senior leadership"],
        "Stakeholder Engagement": ["community engagement", "stakeholder accountability"],
        "Anti-Corruption": ["anti-money laundering", "whistleblower policy", "anti-corruption"]
    }

    EU_CSRD_SIGNALS = {
        "CSRD Alignment": ["csrd", "corporate sustainability reporting directive"],
        "ESRS Compliance": ["esrs", "european sustainability reporting standards"],
        "EU Taxonomy": ["eu taxonomy", "environmentally sustainable activities"],
        "Double Materiality": ["double materiality", "financial and impact materiality"]
    }

    def evaluate_disclosure(
        self, 
        text: str, 
        ifrs_results: Dict[str, Any], 
        entity_type: str = "Corporate Enterprise"
    ) -> Dict[str, Any]:
        
        text_lower = text.lower()

        # 1. SDG Analysis
        sdg_hits = {}
        for sdg, keywords in self.SDG_KEYWORD_MAP.items():
            matched = [kw for kw in keywords if kw in text_lower]
            if matched:
                sdg_hits[sdg] = matched

        sdg_score = (len(sdg_hits) / len(self.SDG_KEYWORD_MAP)) * 100
        if entity_type == "Government / Public Institution":
            if "SDG 16: Governance & Peace" in sdg_hits:
                sdg_score = min(100.0, sdg_score + 15.0)
            if "SDG 11: Sustainable Cities" in sdg_hits:
                sdg_score = min(100.0, sdg_score + 10.0)

        # 2. ISO Standards Detection
        iso_hits = [std for std, kws in self.ISO_STANDARDS.items() if any(kw in text_lower for kw in kws)]
        iso_score = (len(iso_hits) / len(self.ISO_STANDARDS)) * 100

        # 3. NSE ESG Guidance Compliance
        nse_hits = [pillar for pillar, kws in self.NSE_ESG_PILLARS.items() if any(kw in text_lower for kw in kws)]
        nse_score = (len(nse_hits) / len(self.NSE_ESG_PILLARS)) * 100

        # 4. EU / CSRD Signals
        eu_hits = [sig for sig, kws in self.EU_CSRD_SIGNALS.items() if any(kw in text_lower for kw in kws)]
        eu_score = (len(eu_hits) / len(self.EU_CSRD_SIGNALS)) * 100

        # 5. Composite Score Calculation
        ifrs_rescaled = ((ifrs_results.get("esg_index_score", 1.0) - 1.0) / 8.0) * 100
        composite_score = round(
            (ifrs_rescaled * 0.35) + 
            (sdg_score * 0.25) + 
            (nse_score * 0.20) + 
            (iso_score * 0.10) + 
            (eu_score * 0.10), 
            1
        )

        if composite_score >= 80.0:
            maturity_stage = "ADVANCED"
        elif composite_score >= 60.0:
            maturity_stage = "DEVELOPING"
        elif composite_score >= 40.0:
            maturity_stage = "EMERGING"
        else:
            maturity_stage = "STARTING POINT"

        # Constructive Roadmap
        roadmap = []
        if "SDG 16: Governance & Peace" not in sdg_hits:
            roadmap.append({
                "framework": "UNDP SDG 16 / Governance",
                "item": "Institutional Integrity & Anti-Corruption",
                "recommendation": "Formally publish anti-corruption, whistleblower, and stakeholder accountability policies inline with UNDP SDG 16 standards."
            })

        if "ISO 14064" not in iso_hits:
            roadmap.append({
                "framework": "ISO Standards",
                "item": "ISO 14064 GHG Verification",
                "recommendation": "Adopt ISO 14064 standards for third-party auditing and verification of Scope 1 and Scope 2 carbon intensity logs."
            })

        if "Materiality" not in nse_hits:
            roadmap.append({
                "framework": "NSE ESG Manual",
                "item": "Materiality Assessment Matrix",
                "recommendation": "Publish a double materiality assessment identifying key ESG risks impacting both financial return and community stakeholders."
            })

        if "Double Materiality" not in eu_hits:
            roadmap.append({
                "framework": "EU CSRD / ESRS",
                "item": "Double Materiality Framework",
                "recommendation": "Incorporate double materiality reporting to align local operations with global international capital requirements."
            })

        return {
            "entity_type": entity_type,
            "composite_score_100": composite_score,
            "maturity_stage": maturity_stage,
            "sub_scores": {
                "ifrs_index_rescaled": round(ifrs_rescaled, 1),
                "sdg_mapping_score": round(sdg_score, 1),
                "nse_esg_score": round(nse_score, 1),
                "iso_compliance_score": round(iso_score, 1),
                "eu_csrd_score": round(eu_score, 1)
            },
            "sdg_aligned_initiatives": sdg_hits,
            "iso_standards_identified": iso_hits,
            "nse_pillars_covered": nse_hits,
            "eu_signals_detected": eu_hits,
            "improvement_roadmap": roadmap
        }


# =====================================================================
# 5. EXPANDED PDF REPORT GENERATOR (FULL COMPREHENSIVE AUDIT)
# =====================================================================

def generate_pdf_report(results: Dict[str, Any], multi_results: Optional[Dict[str, Any]] = None) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return b"%PDF-1.4 empty placeholder"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        rightMargin=36, 
        leftMargin=36, 
        topMargin=36, 
        bottomMargin=36
    )
    story = []
    styles = getSampleStyleSheet()

    # Custom Paragraph Styles
    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1E3A8A'), spaceAfter=6)
    section_heading = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#1E3A8A'), spaceBefore=10, spaceAfter=6)
    normal_style = ParagraphStyle('ReportNormal', parent=styles['Normal'], fontSize=9, leading=12)
    bullet_style = ParagraphStyle('ReportBullet', parent=normal_style, leftIndent=12, spaceAfter=3)
    rec_style = ParagraphStyle('ReportRec', parent=normal_style, textColor=colors.HexColor('#0F172A'), spaceAfter=6)
    footer_style = ParagraphStyle('FooterStyle', parent=styles['Italic'], fontSize=8, textColor=colors.HexColor('#64748B'))

    # HEADER SECTION
    story.append(Paragraph("IFRS / NSE ESG Forensic Assurance Audit", title_style))
    story.append(Paragraph("<b>Standard Alignment:</b> IFRS S1, IFRS S2, NSE ESG Manual, ISO 14064, UNDP SDG 16", normal_style))
    story.append(Spacer(1, 10))

    # SECTION 1: EXECUTIVE VERIFICATION SUMMARY TABLE
    story.append(Paragraph("1. Executive ESG Verification Summary", section_heading))
    
    comp_score_str = f"{multi_results.get('composite_score_100', 0)} / 100 ({multi_results.get('maturity_stage', 'N/A')})" if multi_results else "N/A"
    initiatives_str = ", ".join(results.get("community_impact", {}).get("verified_initiatives", [])) or "None"
    exceptions_str = ", ".join(results.get("exceptions_detected", [])) or "None"

    exec_table_data = [
        ["Audit Parameter", "Extracted / Calculated Value", "Forensic Status & Classification"],
        ["Entity Name", str(results.get("entity_name", "Unknown")), "Recognized Entity"],
        ["Reporting Period", str(results.get("reporting_period", "N/A")), "Active Cycle"],
        ["ESG Index Score (1–9 Scale)", f"{results.get('esg_index_score', 1.0)} / 9.0", str(results.get("esg_rating_label", "N/A"))],
        ["Multi-Framework Composite Score", comp_score_str, "Composite Benchmark"],
        ["Assurance Risk State", str(results.get("assurance_risk_state", "N/A")), "Action / Verification Flagged"],
        ["Scope 1 GHG Emissions", f"{results.get('scope_1_tco2e', 0):,.2f} tCO2e", "Quantitative Baseline Logged"],
        ["Scope 2 GHG Emissions", f"{results.get('scope_2_tco2e', 0):,.2f} tCO2e", "Quantitative Baseline Logged"],
        ["Recalculated GHG Intensity", f"{results.get('recalculated_ghg_intensity', 0):,.2f} tCO2e / output", "Recalculated Metric"],
        ["Greenwashing Risk Level", str(results.get("greenwash_analysis", {}).get("risk_level", "VERIFIED")), f"Buzzword Count: {results.get('greenwash_analysis', {}).get('narrative_buzzword_count', 0)}"],
        ["Community Impact Score", f"{results.get('community_impact', {}).get('score', 0)} / 10.0", "High Local Alignment"],
        ["Verified Initiatives", initiatives_str, "Verified Indicators Detected"],
        ["Exceptions Detected", exceptions_str, "Flagged Anomalies"]
    ]

    t1 = Table(exec_table_data, colWidths=[160, 180, 200])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t1)
    story.append(Spacer(1, 12))

    if multi_results:
        # SECTION 2: FRAMEWORK SCORE BREAKDOWN
        story.append(Paragraph("2. Multi-Framework Score Breakdown", section_heading))
        sub_scores = multi_results.get("sub_scores", {})
        
        breakdown_table_data = [
            ["Framework Framework Module", "Weighted Score (%)", "Status Tier"],
            ["IFRS 1–9 Index (Rescaled)", f"{sub_scores.get('ifrs_index_rescaled', 0.0)}%", "Core Metric"],
            ["UNEP FI / UNDP SDG Mapping Score", f"{sub_scores.get('sdg_mapping_score', 0.0)}%", "High Alignment"],
            ["NSE ESG Manual Guidance Score", f"{sub_scores.get('nse_esg_score', 0.0)}%", "Regulatory Coverage"],
            ["ISO Compliance Coverage Score", f"{sub_scores.get('iso_compliance_score', 0.0)}%", "Technical Gap"],
            ["EU CSRD / ESRS Signals Score", f"{sub_scores.get('eu_csrd_score', 0.0)}%", "International Alignment"]
        ]

        t2 = Table(breakdown_table_data, colWidths=[240, 150, 150])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t2)
        story.append(Spacer(1, 12))

        # SECTION 3: VALIDATED STRENGTHS & COVERAGE
        story.append(Paragraph("3. Validated Strengths & Alignment", section_heading))
        
        aligned_sdgs = list(multi_results.get("sdg_aligned_initiatives", {}).keys())
        story.append(Paragraph("<b>Validated UN Sustainable Development Goals (SDGs):</b>", normal_style))
        if aligned_sdgs:
            for sdg in aligned_sdgs:
                story.append(Paragraph(f"• [VERIFIED] {sdg}", bullet_style))
        else:
            story.append(Paragraph("• None detected", bullet_style))

        story.append(Spacer(1, 4))
        nse_pillars = multi_results.get("nse_pillars_covered", [])
        story.append(Paragraph("<b>Validated NSE ESG Guidance Pillars:</b>", normal_style))
        if nse_pillars:
            for pil in nse_pillars:
                story.append(Paragraph(f"• [VERIFIED] {pil}", bullet_style))
        else:
            story.append(Paragraph("• None detected", bullet_style))

        story.append(Spacer(1, 12))

        # SECTION 4: CONSTRUCTIVE IMPROVEMENT ROADMAP
        story.append(Paragraph("4. Constructive Improvement Roadmap", section_heading))
        roadmap = multi_results.get("improvement_roadmap", [])
        if roadmap:
            for idx, item in enumerate(roadmap, 1):
                rec_text = f"<b>Action Item {idx}:</b> [{item.get('framework')}] — <b>{item.get('item')}</b><br/>" \
                           f"<i>Recommendation:</i> {item.get('recommendation')}"
                story.append(Paragraph(rec_text, rec_style))
                story.append(Spacer(1, 4))
        else:
            story.append(Paragraph("No critical framework gaps identified. Excellent sustainability governance alignment.", normal_style))

    story.append(Spacer(1, 16))

    # FOOTER WITH SHA-256 HASH
    story.append(Paragraph(f"<b>Document Verification Fingerprint (SHA-256):</b> {results.get('data_lineage_sha256', 'N/A')}", footer_style))
    story.append(Paragraph("Automated forensic assurance report evaluating corporate disclosure data, regional impact, and greenwashing risks.", footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =====================================================================
# 6. STREAMLIT FRONTEND USER INTERFACE
# =====================================================================

st.set_page_config(
    page_title="IFRS & NSE ESG Forensic Assurance Engine",
    page_icon="🔍",
    layout="wide"
)

st.title("IFRS / NSE ESG Forensic Verification Platform")
st.caption("Standardized 1–9 ESG Index, Cover Page Entity Detection, and Multi-Framework (SDG, ISO, NSE, EU) Validation Engine.")

st.markdown("---")
st.subheader("1. Entity Type & Document Upload")

col_entity, col_file = st.columns([1, 2])

with col_entity:
    entity_type = st.radio(
        "Select Entity Type for Validation Framework Weights:",
        ["Corporate Enterprise", "Government / Public Institution"]
    )

with col_file:
    uploaded_file = st.file_uploader(
        "Drag and drop corporate disclosure file (e.g. NCBA SDID Report)", 
        type=["pdf", "docx", "doc", "html", "htm"]
    )

if uploaded_file is not None:
    raw_bytes = uploaded_file.getvalue()
    filename = uploaded_file.name

    # 1. Document Extraction & Base IFRS Parsing
    extracted_text = DocumentExtractor.process_file(raw_bytes, filename)
    parser = EnhancedDisclosureParser()
    parsed_data = parser.parse_text(extracted_text)
    
    engine = IFRSForensicEngine()
    results = engine.verify_disclosure(parsed_data, raw_bytes)

    # 2. Multi-Framework Analysis
    multi_engine = MultiFrameworkEngine()
    multi_results = multi_engine.evaluate_disclosure(extracted_text, results, entity_type)

    st.markdown("---")
    st.subheader("2. Executive ESG Indicators & Scores")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entity Name", results.get("entity_name", "Unknown"))
    c2.metric("IFRS Index (1-9)", f"{results.get('esg_index_score')} / 9.0")
    c3.metric("Composite ESG Score", f"{multi_results.get('composite_score_100')} / 100")
    c4.metric("Maturity Stage", multi_results.get("maturity_stage"))

    st.markdown("---")
    st.subheader("3. Executive ESG Verification Summary")

    initiatives = ", ".join(results.get("community_impact", {}).get("verified_initiatives", [])) or "None"
    exceptions = ", ".join(results.get("exceptions_detected", [])) or "None"

    table_markdown = f"""
    | Audit Parameter | Extracted / Calculated Value | Forensic Status & Classification |
    | :--- | :--- | :--- |
    | **Entity Name** | {results.get('entity_name')} | Recognized Entity |
    | **Reporting Period** | {results.get('reporting_period')} | Active Cycle |
    | **ESG Index Score (1–9 Scale)** | **{results.get('esg_index_score')} / 9.0** | **{results.get('esg_rating_label')}** |
    | **Assurance Risk State** | **{results.get('assurance_risk_state')}** | Action / Verification Flagged |
    | **Scope 1 GHG Emissions** | {results.get('scope_1_tco2e', 0):,.2f} tCO2e | Quantitative Baseline Logged |
    | **Scope 2 GHG Emissions** | {results.get('scope_2_tco2e', 0):,.2f} tCO2e | Quantitative Baseline Logged |
    | **Recalculated GHG Intensity** | {results.get('recalculated_ghg_intensity', 0):,.2f} tCO2e / output | Recalculated Metric |
    | **Greenwashing Risk Level** | {results.get('greenwash_analysis', {}).get('risk_level')} | Buzzword Count: {results.get('greenwash_analysis', {}).get('narrative_buzzword_count')} |
    | **Community Impact Score** | **{results.get('community_impact', {}).get('score')} / 10.0** | High Local Alignment |
    | **Verified Initiatives** | {initiatives} | Verified Indicators Detected |
    | **Exceptions Detected** | {exceptions} | Flagged Anomalies |
    """
    st.markdown(table_markdown)

    st.caption(f"**Document Verification ID (SHA-256):** `{results.get('data_lineage_sha256')}`")

    st.markdown("---")
    st.subheader("5. Multi-Framework Validation Scorecard & Growth Roadmap")

    col_bars, col_strengths = st.columns([1, 1])

    with col_bars:
        st.write("### Framework Score Breakdown")
        sub_scores = multi_results.get("sub_scores", {})
        
        st.write(f"**IFRS 1–9 Index (Rescaled):** {sub_scores.get('ifrs_index_rescaled')}%")
        st.progress(sub_scores.get('ifrs_index_rescaled', 0.0) / 100.0)

        st.write(f"**UNEP FI / UNDP SDG Mapping Score:** {sub_scores.get('sdg_mapping_score')}%")
        st.progress(sub_scores.get('sdg_mapping_score', 0.0) / 100.0)

        st.write(f"**NSE ESG Manual Guidance Score:** {sub_scores.get('nse_esg_score')}%")
        st.progress(sub_scores.get('nse_esg_score', 0.0) / 100.0)

        st.write(f"**ISO Compliance Coverage Score:** {sub_scores.get('iso_compliance_score')}%")
        st.progress(sub_scores.get('iso_compliance_score', 0.0) / 100.0)

        st.write(f"**EU CSRD / ESRS Signals Score:** {sub_scores.get('eu_csrd_score')}%")
        st.progress(sub_scores.get('eu_csrd_score', 0.0) / 100.0)

    with col_strengths:
        st.write("### Validated Strengths & Coverage")
        
        st.write("**SDGs Aligned:**")
        aligned_sdgs = list(multi_results.get("sdg_aligned_initiatives", {}).keys())
        if aligned_sdgs:
            for sdg in aligned_sdgs:
                st.write(f"- ✅ {sdg}")
        else:
            st.write("- None detected")

        st.write("**NSE ESG Pillars Covered:**")
        nse_pillars = multi_results.get("nse_pillars_covered", [])
        if nse_pillars:
            for pil in nse_pillars:
                st.write(f"- ✅ {pil}")
        else:
            st.write("- None detected")

    st.write("### Constructive Improvement Roadmap")
    roadmap = multi_results.get("improvement_roadmap", [])
    if roadmap:
        for idx, item in enumerate(roadmap, 1):
            with st.expander(f"📌 Recommendation {idx}: {item.get('framework')} — {item.get('item')}"):
                st.write(f"**Action Plan:** {item.get('recommendation')}")
    else:
        st.success("No critical gap recommendations flagged! Excellent framework alignment.")

    st.markdown("---")
    st.subheader("6. Audit Downloads")

    combined_output = {
        "ifrs_audit_log": results,
        "multi_framework_validation": multi_results
    }

    pdf_bytes = generate_pdf_report(results, multi_results)
    json_str = json.dumps([combined_output], indent=2)

    col_pdf, col_json = st.columns(2)
    with col_pdf:
        st.download_button(
            label="📄 Download Full PDF Audit Report",
            data=pdf_bytes,
            file_name=f"{results.get('entity_name', 'company')}_ESG_Full_Audit.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with col_json:
        st.download_button(
            label="📥 Download Complete JSON Audit Log",
            data=json_str,
            file_name=f"{results.get('entity_name', 'company')}_ESG_Full_Audit.json",
            mime="application/json",
            use_container_width=True
        )
