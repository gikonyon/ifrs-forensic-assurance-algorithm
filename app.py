import json
import streamlit as st
from src.forensic_algorithm import (
    IFRSForensicEngine, 
    DocumentExtractor, 
    EnhancedDisclosureParser, 
    generate_pdf_report
)

st.set_page_config(
    page_title="IFRS & NSE ESG Forensic Assurance Engine",
    page_icon="🔍",
    layout="wide"
)

st.title("IFRS / NSE ESG Forensic Verification Platform")
st.caption("Standardized 1–9 ESG Index, Cover Page Entity Detection, and Greenwashing Verification.")

st.markdown("---")
st.subheader("1. Upload Sustainability Disclosure (PDF, Word, or HTML)")

uploaded_file = st.file_uploader(
    "Drag and drop corporate disclosure file (e.g. NCBA SDID Report)", 
    type=["pdf", "docx", "doc", "html", "htm"]
)

if uploaded_file is not None:
    raw_bytes = uploaded_file.getvalue()
    filename = uploaded_file.name

    extracted_text = DocumentExtractor.process_file(raw_bytes, filename)
    parser = EnhancedDisclosureParser()
    parsed_data = parser.parse_text(extracted_text)
    
    engine = IFRSForensicEngine()
    results = engine.verify_disclosure(parsed_data, raw_bytes)

    st.markdown("---")
    st.subheader("2. Key ESG & Forensic Indicators")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entity Name", results.get("entity_name", "Unknown"))
    c2.metric("ESG Index (1-9)", f"{results.get('esg_index_score')} / 9.0")
    c3.metric("Rating Tier", results.get("esg_rating_label"))
    c4.metric("Assurance State", results.get("assurance_risk_state"))

    st.markdown("---")
    st.subheader("3. Executive ESG Verification Summary")

    # Render Audit Table directly on interface
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
    st.subheader("4. Downloads & Audit Logs")

    pdf_bytes = generate_pdf_report(results)
    json_str = json.dumps([results], indent=2)

    col_pdf, col_json = st.columns(2)
    with col_pdf:
        st.download_button(
            label="📄 Download Formatted PDF Audit Report",
            data=pdf_bytes,
            file_name=f"{results.get('entity_name', 'company')}_ESG_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with col_json:
        st.download_button(
            label="📥 Download JSON Verification Log",
            data=json_str,
            file_name=f"{results.get('entity_name', 'company')}_ESG_Report.json",
            mime="application/json",
            use_container_width=True
        )
