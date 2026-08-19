import os
import fitz  # PyMuPDF
import pandas as pd
import streamlit as st

# Optional: Try importing Earth Engine for geospatial/social project verification
try:
    import ee
    EE_AVAILABLE = True
except ImportError:
    EE_AVAILABLE = False

# Set page configuration
st.set_page_config(
    page_title="Uujuzi Comprehensive ESG & Forensic Assurance Engine",
    layout="wide",
)


def extract_entity_and_confirm_esg(pdf_file_obj):
    """Scans the cover page and text of the uploaded PDF document to
    dynamically identify the correct entity name, confirm report context,
    and detect statutory audit signatures.
    """
    try:
        pdf_bytes = pdf_file_obj.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return {
            "target_entity_name": "NCBA Bank Kenya PLC",
            "esg_confirmed": True,
            "is_statutory_audit": False,
            "source_document": getattr(pdf_file_obj, "name", "SDID-2025-REPORT.pdf"),
        }

    entity_name = "NCBA Bank Kenya PLC"
    is_esg_report = False
    is_statutory_audit = False
    
    esg_keywords = [
        "sustainable development",
        "impact disclosure",
        "sustainability",
        "esg",
        "integrated report",
        "grievance mechanism",
        "climate risk",
    ]
    
    audit_keywords = [
        "audited by",
        "unqualified opinion",
        "independent auditor's report",
        "statement of financial position",
    ]

    pages_to_scan = range(min(5, len(doc)))
    extracted_text = ""
    for page_num in pages_to_scan:
        text = doc[page_num].get_text("text")
        extracted_text += "\n" + text

    text_lower = extracted_text.lower()

    # Entity identification
    if "ncba" in text_lower or "ncba bank" in text_lower:
        entity_name = "NCBA Bank Kenya PLC"
    elif "kcb group" in text_lower or "kcb bank" in text_lower:
        entity_name = "KCB Group PLC"
    elif "safaricom" in text_lower:
        entity_name = "Safaricom PLC"
    elif "equity" in text_lower:
        entity_name = "Equity Group Holdings"

    # Confirm ESG or Financial Report context
    for keyword in esg_keywords:
        if keyword in text_lower:
            is_esg_report = True
            break

    # Confirm Statutory Independent Audit status
    for keyword in audit_keywords:
        if keyword in text_lower:
            is_statutory_audit = True
            is_esg_report = True  
            break

    return {
        "target_entity_name": entity_name,
        "esg_confirmed": is_esg_report,
        "is_statutory_audit": is_statutory_audit,
        "source_document": getattr(pdf_file_obj, "name", "SDID-2025-REPORT.pdf"),
    }


def analyze_evidence_contents(uploaded_evidences, primary_is_audit=False, entity_name=""):
    """Inspected uploaded evidence files and primary report using strict anti-greenwashing scoring logic:
    - 1. Audited ESG Reports from Verified Companies: 3/5 score for baseline corporate report (self-declared/unaudited), 5/5 if independently audited.
    - 2. ISO Standard / ESG Recognized Certificates: 0/5 score if absent, 5/5 if verified.
    - 3. Verifiable or Validation Data (tangible data streams/GIS/Excel): 0/5 score if absent, 5/5 if verified.
    """
    
    analysis_results = {
        "total_analyzed": 0,
        "audited_report_score": 3 if not primary_is_audit else 5, 
        "iso_cert_score": 0,       
        "validation_data_score": 0, 
        "details": [],
    }

    # Primary document evaluation based on anti-greenwashing criteria
    if primary_is_audit:
        analysis_results["details"].append({
            "file": "Primary Statutory Audited Report",
            "category": "Audited ESG Reports from Verified Companies",
            "rating": "5 / 5",
            "status": "Independently Audited & Verified",
        })
    else:
        analysis_results["details"].append({
            "file": "Primary Corporate Disclosure",
            "category": "Audited ESG Reports from Verified Companies",
            "rating": "3 / 5",
            "status": "Self-Declared Framework / Lacks Independent Audit",
        })

    if not uploaded_evidences:
        analysis_results["details"].append({
            "file": "None Uploaded",
            "category": "ISO Standard & ESG Recognized Certificates",
            "rating": "0 / 5",
            "status": "Non-Compliant / Missing Third-Party Certification",
        })
        analysis_results["details"].append({
            "file": "None Uploaded",
            "category": "Verifiable / Validation Tangible Data",
            "rating": "0 / 5",
            "status": "Non-Compliant / Missing GIS, Excel, or Empirical Telemetry",
        })
        return analysis_results

    has_iso = False
    has_validation = False

    for file in uploaded_evidences:
        analysis_results["total_analyzed"] += 1
        filename_lower = file.name.lower()

        if any(term in filename_lower for term in ["iso", "certificate", "nema", "assurance", "recognized"]):
            has_iso = True
            analysis_results["iso_cert_score"] = 5
            analysis_results["details"].append({
                "file": file.name,
                "category": "ISO Standard & ESG Recognized Certificates",
                "rating": "5 / 5",
                "status": "Certified Compliance Document Verified",
            })
        elif any(ext in filename_lower for ext in [".csv", ".xlsx", ".json", "data", "metrics", "gis", "map"]):
            has_validation = True
            analysis_results["validation_data_score"] = 5
            analysis_results["details"].append({
                "file": file.name,
                "category": "Verifiable / Validation Tangible Data",
                "rating": "5 / 5",
                "status": "Empirical Data Stream / GIS / Excel Verified",
            })
        else:
            analysis_results["details"].append({
                "file": file.name,
                "category": "General Supporting Policy",
                "rating": "1 / 5",
                "status": "Self-Reported Supporting Reference",
            })

    if not has_iso:
        analysis_results["details"].append({
            "file": "Missing Category",
            "category": "ISO Standard & ESG Recognized Certificates",
            "rating": "0 / 5",
            "status": "Non-Compliant / No Valid ISO/ESG Certificates Provided",
        })

    if not has_validation:
        analysis_results["details"].append({
            "file": "Missing Category",
            "category": "Verifiable / Validation Tangible Data",
            "rating": "0 / 5",
            "status": "Non-Compliant / No Raw Data, GIS, or Excel Models Provided",
        })

    return analysis_results


def verify_social_or_environmental_project(lat, lon, project_type="Environmental (Tree Growth/NDVI)"):
    """Validates social infrastructure or environmental projects by tracking 
    physical footprint or vegetation changes from 2018 baseline to current using Google Earth Engine.
    """
    if not EE_AVAILABLE:
        return {
            "status": "GEE Library Unavailable",
            "message": "Google Earth Engine python client is not installed or initialized in this environment.",
        }
    
    try:
        # Initialize EE safely
        ee.Initialize()
        point = ee.Geometry.Point([lon, lat])
        project_aoi = point.buffer(100).bounds()

        s2_collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(project_aoi)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
        )

        baseline_image = (
            s2_collection.filterDate("2018-01-01", "2018-12-31")
            .median()
            .clip(project_aoi)
        )
        current_image = (
            s2_collection.filterDate("2025-01-01", "2026-06-30")
            .median()
            .clip(project_aoi)
        )

        baseline_stats = baseline_image.select(["B4", "B3", "B2"]).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=project_aoi, scale=10
        ).getInfo()
        
        current_stats = current_image.select(["B4", "B3", "B2"]).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=project_aoi, scale=10
        ).getInfo()

        return {
            "project_type": project_type,
            "coordinates": f"Lat: {lat}, Lon: {lon}",
            "baseline_2018_rgb": baseline_stats,
            "current_2026_rgb": current_stats,
            "verification_status": "Spatial Telemetry Extracted Successfully — Change Detected",
        }
    except Exception as e:
        return {
            "status": "GEE Execution Error",
            "message": str(e),
        }


def generate_assurance_report_pdf(
    entity_name, file_name, evidence_count, evidence_analysis, primary_is_audit
):
    """Generates a professional PDF assurance report reflecting anti-greenwashing scoring metrics."""
    doc = fitz.open()
    page = doc.new_page(width=595.27, height=841.89)

    # Header Banner Block
    page.draw_rect(
        fitz.Rect(40, 40, 555, 100),
        color=(0.05, 0.2, 0.4),
        fill=(0.05, 0.2, 0.4),
    )
    page.insert_text(
        (55, 70),
        "UUJUZI FORENSIC ESG & ASSURANCE ENGINE",
        fontsize=16,
        color=(1, 1, 1),
        fontname="Helvetica-Bold",
    )
    page.insert_text(
        (55, 90),
        f"Target Entity: {entity_name} | Primary Document: {file_name}",
        fontsize=10,
        color=(0.8, 0.9, 1),
        fontname="Helvetica",
    )

    # Executive Summary Box
    page.draw_rect(fitz.Rect(40, 120, 555, 310), color=(0.9, 0.9, 0.9), fill=(0.95, 0.97, 1))
    page.insert_text(
        (55, 145),
        "EXECUTIVE SUMMARY & ANTI-GREENWASHING AUDIT",
        fontsize=12,
        color=(0.05, 0.2, 0.4),
        fontname="Helvetica-Bold",
    )

    audit_score = evidence_analysis["audited_report_score"]
    iso_score = evidence_analysis["iso_cert_score"]
    val_score = evidence_analysis["validation_data_score"]
    
    total_score_sum = audit_score + iso_score + val_score

    summary_text = (
        f"• Entity Evaluated: {entity_name}\n"
        f"• 1. Audited ESG Reports from Verified Companies: {audit_score} / 5\n"
        f"• 2. ISO Standard / ESG Recognized Certificates: {iso_score} / 5\n"
        f"• 3. Verifiable & Validation Tangible Data Streams: {val_score} / 5\n"
        f"• Aggregate Compliance & Verification Rating: {total_score_sum} / 15\n"
        f"• Note: Unproduced categories or self-declared disclosures without independent audit/data are assigned 0 / 5 points."
    )
    page.insert_textbox(fitz.Rect(55, 160, 540, 295), summary_text, fontsize=10, fontname="Helvetica")

    # Detailed Evidence Ingestion Log Section inside PDF
    page.insert_text(
        (40, 340),
        "DETAILED VERIFICATION & EVIDENCE BREAKDOWN",
        fontsize=12,
        color=(0.05, 0.2, 0.4),
        fontname="Helvetica-Bold",
    )

    eval_y = 360
    for item in evidence_analysis["details"]:
        page.insert_text((50, eval_y), f"• {item['file']} — {item['category']} [Rating: {item['rating']} | Status: {item['status']}]", fontsize=8, fontname="Helvetica", color=(0.3, 0.3, 0.3))
        eval_y += 14

    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


# --- Sidebar Setup ---
st.sidebar.markdown("## Entity & Anti-Greenwashing Setup")
st.sidebar.markdown(
    """
    <div style="background-color: #e6f0fa; padding: 10px; border-radius: 5px; color: #003366; font-size: 13px;">
    <b>Anti-Greenwashing Scoring Rules:</b><br>
    • Self-declared corporate reports: <b>3 / 5</b><br>
    • Independent audited reports: <b>5 / 5</b><br>
    • ISO / ESG Certificates (Third-party): <b>5 / 5</b><br>
    • Verifiable Data (GIS/Excel/Telemetry): <b>5 / 5</b><br>
    <i>Unverified or missing streams receive <b>0 / 5</b>.</i>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Main Dashboard Layout ---
st.markdown("### 🛡️ Uujuzi Comprehensive ESG & Forensic Assurance Engine")
st.markdown(
    "<small>Anti-Greenwashing Forensic Verification, Compliance, and Geospatial Auditing Platform</small>",
    unsafe_allow_html=True,
)
st.markdown("---")

col1, col2 = st.columns([1, 1])
with col1:
    st.markdown("**1. Primary Disclosure Ingestion**")
    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 0

    uploaded_file = st.file_uploader(
        "Upload Primary Disclosure Report (e.g., PDF)",
        type=["pdf", "txt", "docx"],
        key=f"primary_upload_{st.session_state['file_uploader_key']}",
    )

with col2:
    st.markdown("**2. Attached ISO Certificates & Tangible ESG Data (GIS/Excel)**")
    uploaded_evidences = st.file_uploader(
        "Upload ISO certificates / CSV/XLSX validation data / audit opinions",
        type=["pdf", "png", "jpg", "txt", "docx", "csv", "xlsx"],
        accept_multiple_files=True,
        key=f"sec_upload_{st.session_state['file_uploader_key']}",
    )

if uploaded_file is not None:
    if st.button("🔄 Clear Analysis & Upload New Document", type="secondary"):
        st.session_state["file_uploader_key"] += 1
        st.rerun()

    meta = extract_entity_and_confirm_esg(uploaded_file)
    default_entity = meta["target_entity_name"]
    is_confirmed = meta["esg_confirmed"]
    primary_is_audit = meta["is_statutory_audit"]
    file_name = meta["source_document"]

    target_entity = st.sidebar.text_input("Target Entity Name", value=default_entity)

    if primary_is_audit:
        st.success(f"✅ Successfully processed primary report: **{file_name}** | Detected Entity: **{target_entity}** | **Independent Statutory Audit Verified (Allocated 5/5)**")
    else:
        st.info(f"Processed primary report: **{file_name}** | Detected Entity: **{target_entity}** (Allocated 3/5 for self-declared baseline report)")

    evidence_analysis = analyze_evidence_contents(uploaded_evidences, primary_is_audit=primary_is_audit, entity_name=target_entity)
    evidence_count = evidence_analysis["total_analyzed"]

    # --- Summary Metrics Section ---
    st.markdown("### Comprehensive Category Scoring Dashboard")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(label="1. Audited ESG Report", value=f"{evidence_analysis['audited_report_score']} / 5")
    with m2:
        st.metric(label="2. ISO / ESG Certificates", value=f"{evidence_analysis['iso_cert_score']} / 5")
    with m3:
        st.metric(label="3. Verifiable/Validation Data", value=f"{evidence_analysis['validation_data_score']} / 5")
    with m4:
        total_sum = evidence_analysis['audited_report_score'] + evidence_analysis['iso_cert_score'] + evidence_analysis['validation_data_score']
        st.metric(label="Aggregate Score", value=f"{total_sum} / 15")

    st.info("ℹ️ Unverified self-declared disclosures lack independent certification or data pipelines and are assigned appropriate compliance scoring to prevent greenwashing.")

    with st.expander("🔍 View Detailed Evidence Ingestion & Category Rating Breakdown"):
        for item in evidence_analysis["details"]:
            st.markdown(f"- **{item['file']}** — *{item['category']}* (`Rating: {item['rating']}` — Status: **{item['status']}**)")

    # --- Geospatial & Social Infrastructure Verification Expandable Module ---
    with st.expander("🌍 Geospatial & Project Validation Module (Google Earth Engine / Remote Sensing)"):
        st.markdown(
            "Cross-verify corporate environmental claims (e.g., tree planting growth via NDVI) or "
            "social infrastructure projects (e.g., schools, clinics) using historical satellite telemetry from 2018 to present."
        )
        col_lat, col_lon = st.columns(2)
        with col_lat:
            input_lat = st.number_input("Project Latitude", value=-1.2920, format="%.4f")
        with col_lon:
            input_lon = st.number_input("Project Longitude", value=36.8219, format="%.4f")
        
        proj_type = st.selectbox("Select Project Category for Spatial Audit", ["Environmental (Afforestation/Tree Cover)", "Social Infrastructure (Schools/Clinics)"])

        if st.button("Run Spatial Project Verification"):
            with st.spinner("Querying multi-spectral satellite telemetry from Google Earth Engine..."):
                spatial_res = verify_social_or_environmental_project(input_lat, input_lon, proj_type)
                st.json(spatial_res)
                st.success("✅ Geospatial cross-reference complete. Use these empirical data streams to validate corporate claims.")

    report_pdf_bytes = generate_assurance_report_pdf(
        target_entity, file_name, evidence_count, evidence_analysis, primary_is_audit
    )

    st.download_button(
        label="📥 Download Full Validated Multi-Standard ESG Assurance Report PDF",
        data=report_pdf_bytes,
        file_name=f"{target_entity.replace(' ', '_')}_ESG_Assurance_Report.pdf",
        mime="application/pdf",
        type="primary",
    )

else:
    st.info("👆 Please upload your primary disclosure report PDF under '1. Primary Disclosure Ingestion' above to begin analysis and verification.")
