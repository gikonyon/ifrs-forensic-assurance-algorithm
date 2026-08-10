import json
import csv
import streamlit as st
from src.forensic_algorithm import IFRSForensicEngine, DocumentExtractor, DisclosureParser

st.set_page_config(
    page_title="IFRS Forensic Assurance Engine",
    page_icon="🔍",
    layout="wide"
)

# Email Lead Capture Session State
if "registered" not in st.session_state:
    st.session_state.registered = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

st.title("IFRS S1 / S2 Forensic Verification Engine")
st.caption("Transaction-level analytical assurance for PDF, Word, and HTML disclosures.")

# Sidebar Lead Registration Form
with st.sidebar:
    st.header("Access & Verification")
    if not st.session_state.registered:
        st.subheader("Register to Unlock Full Assurance Reports")
        email_in = st.text_input("Enter your business email:", placeholder="name@company.com")
        if st.button("Access Full Engine"):
            if "@" in email_in and "." in email_in:
                st.session_state.registered = True
                st.session_state.user_email = email_in
                
                with open("registrations.csv", "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([email_in])
                    
                st.success("Registration confirmed!")
                st.rerun()
            else:
                st.error("Please provide a valid email address.")
    else:
        st.success(f"Verified Session: **{st.session_state.user_email}**")
        if st.button("Clear Session"):
            st.session_state.registered = False
            st.session_state.user_email = ""
            st.rerun()

st.markdown("---")
st.subheader("1. Upload Sustainability Disclosure (PDF, Word, or HTML)")

uploaded_file = st.file_uploader(
    "Drag and drop your file here", 
    type=["pdf", "docx", "doc", "html", "htm"],
    help="Upload an IFRS disclosure document in PDF, MS Word, or HTML format."
)

if uploaded_file is not None:
    raw_bytes = uploaded_file.getvalue()
    filename = uploaded_file.name

    # Extract text content based on file type
    extracted_text = DocumentExtractor.process_file(raw_bytes, filename)
    
    # Parse ESG variables
    parser = DisclosureParser()
    parsed_data = parser.parse_text(extracted_text)
    
    # Run forensic engine
    engine = IFRSForensicEngine()
    results = engine.verify_disclosure(parsed_data, raw_bytes)

    st.markdown("---")
    st.subheader("2. Key Forensic Indicators")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entity Name", results.get("entity_name", "Unknown"))
    c2.metric("GHG Intensity", f"{results.get('recalculated_ghg_intensity', 0):.4f}")
    c3.metric("Governance HHI", f"{results.get('governance_hhi', 0):.4f}")
    c4.metric("Assurance Risk State", results.get("assurance_risk_state", "N/A"))

    if st.session_state.registered:
        st.markdown("---")
        st.subheader("3. Audit Trail & SHA-256 Data Lineage")
        st.json(results)
        
        json_str = json.dumps([results], indent=2)
        st.download_button(
            label="📥 Download JSON Report",
            data=json_str,
            file_name=f"{results.get('entity_name', 'entity')}_verification_report.json",
            mime="application/json"
        )
    else:
        st.markdown("---")
        st.warning("🔒 Enter your email address in the sidebar to unlock the detailed SHA-256 lineage audit log and download full JSON/CSV reports.")
