import streamlit as st
import pandas as pd
from models.esg_forensic_engine import (
    extract_entity_from_document,
    classify_assurance_document,
    score_data_pack_metrics,
    check_assurance_coverage,
    detect_restatements,
    evaluate_esg_claim,
    build_verification_report
)

st.set_page_config(
    page_title="Uujuzi Forensic ESG & Assurance Engine", 
    page_icon="🌱", 
    layout="wide"
)

st.title("🌱 Uujuzi Forensic ESG & Assurance Engine")
st.markdown("Automated Greenwashing Detection, Multi-Document Assurance Tiering, Data Pack Scoring, and GIS Spatial Verification")

# Navigation Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📄 Primary ESG Reports", 
    "📜 ISO Standards & Audits", 
    "📊 Supporting Data Packs", 
    "🗺️ GIS Spatial Audit", 
    "🛡️ Boundary Coverage & Gaps",
    "📑 Comprehensive Report"
])

# ---------------------------------------------------------------------------
# TAB 1: Primary ESG Report Ingestion (Multi-File Upload)
# ---------------------------------------------------------------------------
with tab1:
    st.subheader("Primary ESG Report Ingestion")
    st.markdown("Upload one or multiple company primary annual or sustainability reports (PDF/TXT) for entity verification and disclosure checks.")
    
    primary_files = st.file_uploader("Upload Primary ESG Reports", type=["pdf", "txt"], accept_multiple_files=True, key="primary_up")
    
    if primary_files:
        if st.button("Ingest & Verify Primary Reports"):
            for primary_file in primary_files:
                doc_name = primary_file.name
                text_to_analyze = primary_file.getvalue().decode("utf-8", errors="ignore")
                
                entity_res = extract_entity_from_document(text_to_analyze, doc_name)
                restatement_res = detect_restatements(text_to_analyze, doc_name)
                
                st.markdown(f"---")
                st.markdown(f"### File: `{doc_name}`")
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Detected Entity:** {entity_res['detected_entity'] or 'Not identified'} (Confidence: {entity_res['confidence']})")
                with col2:
                    if restatement_res["restatement_disclosed"]:
                        st.warning("⚠️ Prior-year restatement disclosure detected.")
                    else:
                        st.success("No restatement anomalies detected.")
                st.json(entity_res)
    else:
        st.info("Please upload at least one primary ESG report to begin.")

# ---------------------------------------------------------------------------
# TAB 2: ISO Standards & External ESG Audits (Multi-File Upload)
# ---------------------------------------------------------------------------
with tab2:
    st.subheader("ISO Standards & Third-Party Assurance Certifications")
    st.markdown("Upload multiple independent assurance statements, ISO 14064-3 certificates, or ISAE 3000 audit opinions.")
    
    audit_files = st.file_uploader("Upload Audit Opinions & ISO Certificates", type=["pdf", "txt"], accept_multiple_files=True, key="audit_up_multi")
    
    if audit_files:
        if st.button("Classify All Uploaded Certifications"):
            for audit_file in audit_files:
                doc_name = audit_file.name
                text_to_analyze = audit_file.getvalue().decode("utf-8", errors="ignore")
                
                class_res = classify_assurance_document(text_to_analyze, doc_name)
                
                st.markdown(f"---")
                st.markdown(f"### Certification File: `{doc_name}`")
                st.success(f"**Assigned Tier:** {class_res['tier_label']}")
                st.json(class_res)
    else:
        st.info("Please upload one or more certification or audit documents.")

# ---------------------------------------------------------------------------
# TAB 3: Metric-Level Scoring for Supporting Data Packs (CSV/XLSX)
# ---------------------------------------------------------------------------
with tab3:
    st.subheader("Supporting Data Pack Auditor (CSV / Excel)")
    st.markdown("Upload your structured ESG metrics data pack to audit assured markers (`^`).")
    
    data_file = st.file_uploader("Upload Data Pack", type=["csv", "xlsx", "txt"], key="dp_up")
    marker_symbol = st.text_input("Assurance Marker Symbol", "^")
    
    df = pd.DataFrame()
    if data_file is not None:
        try:
            if data_file.name.endswith('.csv'):
                df = pd.read_csv(data_file)
            else:
                df = pd.read_excel(data_file)
        except Exception as e:
            st.error(f"Error reading file: {e}")
    else:
        df = pd.DataFrame({
            "Metric_ID": ["M-01", "M-02", "M-03", "M-04"],
            "Description": [
                "Scope 1 GHG Emissions (tCO2e) ^",
                "Total Water Withdrawal (m3)",
                "Scope 2 Market-Based Emissions ^",
                "Total Recordable Injury Frequency Rate (TRIFR)"
            ],
            "Value": [14250, 85400, 3210, 1.2]
        })
    
    if not df.empty:
        st.write("Data Preview:", df.head())
        
        if st.button("Score Data Pack Metrics"):
            pack_res = score_data_pack_metrics(df, assured_marker=marker_symbol)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Metrics Scanned", pack_res["total_metrics_scanned"])
            col2.metric("Assured Metrics", pack_res["assured_metrics"])
            col3.metric("Unaudited Metrics", pack_res["unaudited_metrics"])
            col4.metric("Assurance Ratio", f"{pack_res['assured_ratio'] * 100}%")
            
            st.dataframe(pd.DataFrame(pack_res["row_level_detail"]))

# ---------------------------------------------------------------------------
# TAB 4: GIS Spatial Claim Auditor
# ---------------------------------------------------------------------------
with tab4:
    st.subheader("GIS Spatial Claim Auditor (2017–2026 Verification Window)")
    entity = st.text_input("Entity Name", "GreenCorp Ltd")
    claim_id = st.text_input("Claim ID", "CLM-2021-04")
    category = st.selectbox("Claim Category", ["Environmental", "Social"])
    metric = st.text_input("Claimed Metric", "5,000 ha of indigenous forest restored and protected since 2017")
    year = st.number_input("Claim Year", min_value=2017, max_value=2026, value=2021)
    
    st.markdown("---")
    st.markdown("**Simulated Satellite & GIS Observation Parameters**")
    base_ndvi = st.slider("Baseline NDVI", 0.0, 1.0, 0.62)
    curr_ndvi = st.slider("Current Observation NDVI", 0.0, 1.0, 0.41)
    
    if st.button("Run Spatial Audit"):
        gis_data = {'baseline_ndvi': base_ndvi, 'current_ndvi': curr_ndvi}
        audit = evaluate_esg_claim(entity, claim_id, category, metric, year, "Polygon(1.2921, 36.8219)", gis_data)
        
        if audit.get("DiscrepancyFlag"):
            st.error(f"Status: {audit['TrustStatus']}")
        else:
            st.success(f"Status: {audit['TrustStatus']}")
            
        st.json(audit)

# ---------------------------------------------------------------------------
# TAB 5: Assurance Scope & Boundary Coverage Check
# ---------------------------------------------------------------------------
with tab5:
    st.subheader("Assurance Scope & Boundary Coverage Check")
    st.info("Ensures all mandatory carbon and emissions scopes are fully covered across uploaded certification documents.")
    
    if st.button("Run Multi-Document Coverage Audit"):
        docs_to_check = []
        if audit_files:
            for f in audit_files:
                docs_to_check.append({"document_name": f.name, "text": f.getvalue().decode("utf-8", errors="ignore")})
        else:
            docs_to_check = [
                {"document_name": "sample_ey_assurance.pdf", "text": "Limited assurance covering Scope 1 Scope 2 financed emissions."}
            ]
            
        coverage = check_assurance_coverage(docs_to_check)
        
        st.write(f"**Complete Coverage Achieved?:** {coverage['coverage_complete']}")
        st.write("**Covered Boundaries:**")
        st.json(coverage["covered_boundaries"])
        
        if coverage["uncovered_boundaries"]:
            st.warning(f"Uncovered Gaps: {coverage['uncovered_boundaries']}")
        else:
            st.success("No scope gaps detected across files!")

# ---------------------------------------------------------------------------
# TAB 6: Comprehensive Verification Report Builder
# ---------------------------------------------------------------------------
with tab6:
    st.subheader("Comprehensive Verification Report Generator")
    st.markdown("Compile all uploaded primary reports, audit certifications, and data packs into a final verification report.")
    
    entity_name_input = st.text_input("Company / Entity Evaluated Name", "Standard Chartered Plc")
    
    if st.button("Generate Final Verified Report"):
        primary_text_sample = primary_files[0].getvalue().decode("utf-8", errors="ignore") if primary_files else "Standard Chartered Plc Annual Report..."
        primary_name_sample = primary_files[0].name if primary_files else "primary_report.pdf"
        
        supporting_docs_sample = []
        if audit_files:
            for f in audit_files:
                supporting_docs_sample.append({"document_name": f.name, "text": f.getvalue().decode("utf-8", errors="ignore")})
        else:
            supporting_docs_sample = [
                {"document_name": "ey-assurance.pdf", "text": "Ernst & Young LLP performed limited assurance in accordance with ISAE 3000 (Revised). Scope 1 Scope 2 financed emissions"}
            ]
            
        sample_dp = [{"document_name": "data_pack.csv", "dataframe": df}] if not df.empty else []
        
        report = build_verification_report(
            entity_name=entity_name_input,
            primary_disclosure_text=primary_text_sample,
            primary_disclosure_name=primary_name_sample,
            supporting_documents=supporting_docs_sample,
            data_pack_dataframes=sample_dp
        )
        
        st.success("Verified ESG Compliance Report Generated Successfully!")
        st.json(report)
