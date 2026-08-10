import os
import json
import csv
import io
import streamlit as st
from src.forensic_algorithm import IFRSForensicEngine, DisclosureHTMLParser

# Set Page Config
st.set_page_config(
    page_title="IFRS Forensic Assurance Engine",
    page_icon="🔍",
    layout="wide"
)

# Initialize Session State for Email Verification
if "user_registered" not in st.session_state:
    st.session_state.user_registered = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

st.title("IFRS S1 / S2 Forensic Verification Platform")
st.caption("Continuous, transaction-level verification for sustainability disclosures.")

# Sidebar: Registration / Email Gate Control
with st.sidebar:
    st.header("Access & Registration")
    if not st.session_state.user_registered:
        st.subheader("Register to Access Full Audit Reports")
        email_input = st.text_input("Enter your business email:", placeholder="name@company.com")
        if st.button("Register & Access"):
            if "@" in email_input and "." in email_input:
                st.session_state.user_registered = True
                st.session_state.user_email = email_input
                # Optional: Log the email to a local CSV/Database
                with open("registrations.csv", "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([email_input])
                st.success("Registration successful! You can now upload and analyze reports.")
                st.rerun()
            else:
                st.error("Please enter a valid email address.")
    else:
        st.success(f"Registered as: **{st.session_state.user_email}**")
        if st.button("Log Out / Change Email"):
            st.session_state.user_registered = False
            st.session_state.user_email = ""
            st.rerun()

# Main App Execution Interface
st.markdown("---")
st.subheader("1. Upload ESG / Sustainability Disclosure (HTML)")

uploaded_file = st.file_uploader(
    "Drag and drop your HTML disclosure file here",
    type=["html", "htm"],
    help="Upload an IFRS S1 or IFRS S2 HTML document for automated verification."
)

if uploaded_file is not None:
    # Read uploaded raw HTML
    raw_html = uploaded_file.getvalue().decode("utf-8", errors="ignore")
    
    # Run Parser & Forensic Engine
    parser = DisclosureHTMLParser()
    parsed_data = parser.extract_variables(raw_html)
    engine = IFRSForensicEngine()
    results = engine.verify_disclosure(parsed_data, raw_html)

    st.markdown("---")
    st.subheader("2. Forensic Analysis Results")

    # Display High-Level Summary Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Entity", results.get("entity_name", "Unknown"))
    col2.metric("GHG Intensity", f"{results.get('recalculated_ghg_intensity', 0):.4f}")
    col3.metric("Governance HHI", f"{results.get('governance_hhi', 0):.4f}")
    col4.metric("Risk State", results.get("assurance_risk_state", "N/A"))

    # Email Gating Check for Detailed Reports
    if st.session_state.user_registered:
        st.markdown("---")
        st.subheader("3. Full Verification Audit Log & Lineage")
        
        st.json(results)

        # Prepare Downloads
        json_bytes = json.dumps([results], indent=2).encode("utf-8")
        st.download_button(
            label="📥 Download Detailed JSON Report",
            data=json_bytes,
            file_name=f"{results.get('entity_name', 'entity')}_verification_report.json",
            mime="application/json"
        )
    else:
        st.markdown("---")
        st.warning("🔒 **Full Audit Trail Locked:** Register your email in the sidebar to download complete JSON/CSV reports and view full SHA-256 evidence lineage.")
