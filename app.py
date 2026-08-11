import json
import csv
import streamlit as st
from src.forensic_algorithm import (
    IFRSForensicEngine, 
    DocumentExtractor, 
    EnhancedDisclosureParser, 
    generate_pdf_report
)

# Set Streamlit Page Layout
st.set_page_config(
    page_title="IFRS & NSE ESG Forensic Assurance Engine",
    page_icon="🔍",
    layout="wide"
)

# Header Section
st.title("IFRS / NSE ESG Forensic Verification Platform")
st.caption("Transaction-level verification, greenwashing detection, and regional impact evaluation.")

st.markdown("---")
st.subheader("1. Upload Sustainability Disclosure (PDF, Word, or HTML)")

# File Uploader Widget
uploaded_file = st.file_uploader(
    "Drag and drop your corporate disclosure document here", 
    type=["pdf", "docx", "doc", "html", "htm"],
    help="Upload an IFRS S1/S2, NSE ESG, or corporate disclosure file."
)

if uploaded_file is not None:
    raw_bytes = uploaded_file.getvalue()
    filename = uploaded_file.name

    # 1. Extract text from uploaded file
    extracted_text = DocumentExtractor.process_file(raw_bytes, filename)
    
    # 2. Parse text for metrics, greenwashing flags, and regional impact
    parser = EnhancedDisclosureParser()
    parsed_data = parser.parse_text(extracted_text)
    
    # 3. Run forensic verification engine
    engine = IFRSForensicEngine()
    results = engine.verify_disclosure(parsed_data, raw_bytes)

    st.markdown("---")
    st.subheader("2. Key ESG & Forensic Indicators")

    # Display High-Level Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entity Name", results.get("entity_name", "Unknown"))
    c2.metric("GHG Intensity", f"{results.get('recalculated_ghg_intensity', 0):.4f}")
    c3.metric("Governance HHI", f"{results.get('governance_hhi', 0):.4f}")
    c4.metric("Assurance Risk State", results.get("assurance_risk_state", "N/A"))

    c5, c6, c7 = st.columns(3)
    c5.metric("Greenwashing Risk", results.get("greenwash_analysis", {}).get("risk_level", "LOW_OR_VERIFIED"))
    c6.metric("Community Impact Score", f"{results.get('community_impact', {}).get('score', 0):.2f}")
    c7.metric("Data Quality Tier", results.get("data_quality", {}).get("tier", "N/A"))

    st.markdown("---")
    st.subheader("3. Instant ESG Audit Reports & Data Lineage")

    # Display Full Analytical JSON Payload
    st.json(results)

    # Generate PDF Report Stream
    pdf_bytes = generate_pdf_report(results)
    json_str = json.dumps([results], indent=2)

    # Download Buttons
    col_pdf, col_json = st.columns(2)
    with col_pdf:
        st.download_button(
            label="📄 Download PDF Audit Report",
            data=pdf_bytes,
            file_name=f"{results.get('entity_name', 'company')}_ESG_Verification_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with col_json:
        st.download_button(
            label="📥 Download JSON Verification Log",
            data=json_str,
            file_name=f"{results.get('entity_name', 'company')}_ESG_Verification_Report.json",
            mime="application/json",
            use_container_width=True
        )
        
