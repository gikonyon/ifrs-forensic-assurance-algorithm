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
st.markdown("Automated Greenwashing Detection, Assurance Tiering, Data Pack Scoring, and GIS Spatial Verification Dashboard")

# Navigation Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📄 Document Classifier", 
    "📊 Data Pack Scoring", 
    "🗺️ GIS Spatial Audit", 
    "🛡️ Boundary Coverage", 
    "🔍 Restatement Detector",
    "📑 Comprehensive Report Builder"
])

# ---------------------------------------------------------------------------
# TAB 1: Document Assurance Tiering
# ---------------------------------------------------------------------------
with tab1:
    st.subheader("Assurance Statement Classifier & Entity Extractor")
    doc_name_input = st.text_input("Document File Name", "sustainability_report_2025.pdf")
    doc_text = st.text_area(
        "Paste Assurance Statement / Report Text:", 
        "Ernst & Young LLP was engaged by Standard Chartered Plc to perform a limited assurance engagement in accordance with International Standard on Assurance Engagements (ISAE) 3000 (Revised)."
    )
    
    if st.button("Run Document Analysis"):
        entity_res = extract_entity_from_document(doc_text, doc_name_input)
        class_res = classify_assurance_document(doc_text, doc_name_input)
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Detected Entity:** {entity_res['detected_entity'] or 'Not explicitly identified in header'} (Confidence: {entity_res['confidence']})")
        with col2:
            st.success(f"**Assigned Tier:** {class_res['tier_label']}")
            
        st.json(class_res)

# ---------------------------------------------------------------------------
# TAB 2: Metric-Level Scoring for Supporting Data Packs (CSV/XLSX)
# ---------------------------------------------------------------------------
with tab2:
    st.subheader("Supporting Data Pack Auditor (CSV / Excel)")
    st.markdown("Upload a tabular data file or use the default test dataframe to check which metrics carry assurance markers (`^`).")
    
    uploaded_file = st.file_uploader("Upload CSV Data Pack File", type=["csv", "txt"])
    marker_symbol = st.text_input("Assurance Marker Symbol", "^")
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Error reading file: {e}")
            df = pd.DataFrame()
    else:
        # Default sample data pack dataframe
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
# TAB 3: GIS Spatial Claim Auditor
# ---------------------------------------------------------------------------
with tab3:
    st.subheader("GIS Spatial Claim Auditor (2017–2026 Verification Window)")
    entity = st.text_input("Entity Name", "GreenCorp Ltd")
    claim_id = st.text_input("Claim ID", "CLM-2021-04")
    category = st.selectbox("Claim Category", ["Environmental", "Social"])
    metric = st.text_input("Claimed Metric", "5,000 ha of indigenous forest restored and protected since 2017")
    year = st.number_input("Claim Year", min_value=2017, max_value=2026, value=2021)
    
    st.markdown("---")
    st.markdown("**Simulated Satellite Observation Parameters**")
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
# TAB 4: Assurance Scope & Boundary Coverage Check
# ---------------------------------------------------------------------------
with tab4:
    st.subheader("Assurance Scope & Boundary Coverage Check")
    st.info("Ensures all mandatory carbon and emissions scopes are fully covered across provider documents.")
    
    if st.button("Run Multi-Document Coverage Audit"):
        sample_docs = [
            {"document_name": "ey-assurance-report.pdf", "text": "Ernst & Young LLP performed limited assurance covering Scope 1 Scope 2 financed emissions facilitated emissions."},
            {"document_name": "se-verification.pdf", "text": "SE Advisory Services verified business travel."},
            {"document_name": "gd-verification.pdf", "text": "Global Documentation verified data centre power usage."}
        ]
        coverage = check_assurance_coverage(sample_docs)
        
        st.write(f"**Complete Coverage Achieved?:** {coverage['coverage_complete']}")
        st.write("**Covered Boundaries:**")
        st.json(coverage["covered_boundaries"])
        
        if coverage["uncovered_boundaries"]:
            st.warning(f"Uncovered Gaps: {coverage['uncovered_boundaries']}")
        else:
            st.success("No scope gaps detected across files!")

# ---------------------------------------------------------------------------
# TAB 5: Restatement & Transparency Disclosure Detector
# ---------------------------------------------------------------------------
with tab5:
    st.subheader("Restatement & Data-Integrity Disclosure Detector")
    restatement_input = st.text_area(
        "Paste Report Text to Scan for Restatements:",
        "Total prior year balances have been restated resulting in an increase of $2.2 billion."
    )
    
    if st.button("Detect Restatements"):
        res_data = detect_restatements(restatement_input, "uploaded_report.pdf")
        if res_data["restatement_disclosed"]:
            st.warning("⚠️ Restatement disclosure detected in text!")
            st.write("**Excerpts Found:**")
            for ex in res_data["restatement_excerpts"]:
                st.code(ex)
        else:
            st.success("No restatement disclosures identified in the provided snippet.")

# ---------------------------------------------------------------------------
# TAB 6: Comprehensive Aggregate Report Builder
# ---------------------------------------------------------------------------
with tab6:
    st.subheader("Comprehensive Verification Report Builder")
    st.markdown("Run the full diagnostic assessment combining primary disclosures, supporting third-party verification files, and data packs.")
    
    entity_name_input = st.text_input("Company / Entity Evaluated", "Standard Chartered Plc")
    primary_text_input = st.text_area("Primary Disclosure Text", "Standard Chartered Plc Annual Report 2025 disclosures...")
    
    if st.button("Generate Comprehensive Report"):
        supporting_docs_sample = [
            {"document_name": "ey-assurance.pdf", "text": "Ernst & Young LLP performed a limited assurance engagement in accordance with ISAE 3000 (Revised). financed emissions facilitated emissions"},
            {"document_name": "se-verification.pdf", "text": "SE Advisory Services provided independent third-party reasonable verification of Scope 3 emissions aligned with ISO 14064-3:2019. business travel"}
        ]
        sample_dp = [{"document_name": "data_pack.csv", "dataframe": df}] if not df.empty else []
        
        report = build_verification_report(
            entity_name=entity_name_input,
            primary_disclosure_text=primary_text_input,
            primary_disclosure_name="primary_report.pdf",
            supporting_documents=supporting_docs_sample,
            data_pack_dataframes=sample_dp
        )
        
        st.success("Verification Report Successfully Generated!")
        st.json(report)
