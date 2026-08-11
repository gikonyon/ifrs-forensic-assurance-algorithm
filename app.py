import json
import streamlit as st
from src.forensic_algorithm import (
    IFRSForensicEngine, 
    DocumentExtractor, 
    EnhancedDisclosureParser, 
    generate_pdf_report
)
from src.multi_framework_engine import MultiFrameworkEngine

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

    # 2. Multi-Framework Analysis (UNEP FI, UNDP SDG 16, ISO, NSE, EU)
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

    # -----------------------------------------------------------------
    # SECTION 5: MULTI-FRAMEWORK SCORECARD & IMPROVEMENT ROADMAP
    # -----------------------------------------------------------------
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

    # -----------------------------------------------------------------
    # DOWNLOADS
    # -----------------------------------------------------------------
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
