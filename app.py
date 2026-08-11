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

    # Process Document
    extracted_text = DocumentExtractor.process_file(raw_bytes, filename)
    parser = EnhancedDisclosureParser()
    parsed_data = parser.parse_text(extracted_text)
    
    engine = IFRSForensicEngine()
    results = engine.verify_disclosure(parsed_data, raw_bytes)

    st.markdown("---")
    st.subheader("2. ESG Performance Index (1 to 9 Scale)")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entity Name", results.get("entity_name", "Unknown"))
    c2.metric("ESG Index (1-9)", f"{results.get('esg_index_score')} / 9.0")
    c3.metric("Rating Tier", results.get("esg_rating_label"))
    c4.metric("Assurance State", results.get("assurance_risk_state"))

    st.markdown("---")
    st.subheader("3. Audit Data Lineage & Downloadable PDF")
    
    st.json(results)

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
