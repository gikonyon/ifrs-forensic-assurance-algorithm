import streamlit as st
import pandas as pd
import datetime

# Import modular compliance components
from modules.evidence_vault import register_evidence_document
from modules.incident_tracker import DOSHSIncidentTracker
from modules.spatial_verifier import validate_spatial_compliance
from modules.gap_analyzer import evaluate_esg_assurance_score

# Page Configuration
st.set_page_config(
    page_title="Uujuzi ESG Assurance Engine",
    page_icon="🛡️",
    layout="wide"
)

# Initialize Session States
if "evidence_vault" not in st.session_state:
    st.session_state.evidence_vault = []
if "incidents_log" not in st.session_state:
    st.session_state.incidents_log = []

# Sidebar Navigation
st.sidebar.title("Uujuzi Platform")
target_sector = st.sidebar.selectbox(
    "Target Sector Focus",
    ["Manufacturing", "Agribusiness & Exporters", "Affordable Housing / Construction", "Commercial Banking (Portfolio E&S)"]
)

st.title("UUJUZI ESG EVIDENCE & FORENSIC ASSURANCE LAYER")
st.caption(f"Real-Economy Compliance Engine | Sector: {target_sector}")

tab_vault, tab_doshs, tab_spatial, tab_readiness = st.tabs([
    "📂 Cryptographic Evidence Vault", 
    "⚠️ DOSHS / WIBA Incident Tracker", 
    "🌍 Spatial & EUDR Geotag Verifier", 
    "📊 IFRS S1/S2 Gap & Audit Engine"
])

# ------------------------------------------
# TAB 1: EVIDENCE VAULT
# ------------------------------------------
with tab_vault:
    st.header("Forensic Evidence Vault")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        doc_type = st.selectbox("Document Classification", [
            "NEMA_EIA_LICENCE",
            "NEMA_ANNUAL_ENVIRONMENTAL_AUDIT",
            "DOSHS_SAFETY_INSPECTION_CERTIFICATE",
            "WIBA_INSURANCE_POLICY",
            "MINIMUM_WAGE_PAYROLL_REGISTER",
            "BOARD_MINUTES_ESG_OVERSIGHT"
        ])
        issuer_id = st.text_input("Issuer / Accreditation ID", placeholder="e.g., NEMA/LEAD/1042")
        uploaded_file = st.file_uploader("Upload Source PDF/Image Evidence", type=["pdf", "png", "jpg"])
        
        if st.button("Register & Lock Evidence", type="primary"):
            if uploaded_file and issuer_id:
                file_bytes = uploaded_file.read()
                record = register_evidence_document(file_bytes, uploaded_file.name, doc_type, issuer_id)
                st.session_state.evidence_vault.append(record)
                st.success(f"Document locked! Hash: {record['sha256_hash'][:16]}...")
            else:
                st.error("Please provide both an accreditation ID and a file.")

    with col2:
        st.subheader("Immutable Vault Register")
        if st.session_state.evidence_vault:
            df_vault = pd.DataFrame(st.session_state.evidence_vault)
            st.dataframe(df_vault[["document_type", "issuer_id", "sha256_hash", "timestamp"]], use_container_width=True)

# ------------------------------------------
# TAB 2: DOSHS / WIBA INCIDENTS
# ------------------------------------------
with tab_doshs:
    st.header("DOSHS / WIBA Incident Engine")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        inc_type = st.radio("Severity", ["non_fatal", "fatal"])
        emp_id = st.text_input("Employee Identifier")
        desc = st.text_area("Incident Description")
        
        if st.button("Log Incident"):
            if emp_id and desc:
                tracker = DOSHSIncidentTracker(inc_type, desc, emp_id)
                inc_id = f"INC-{len(st.session_state.incidents_log)+1:03d}"
                payload = tracker.generate_payload(inc_id)
                st.session_state.incidents_log.append(payload)
                st.warning(f"Incident Logged. DOSHS Deadline: {payload['doshs_deadline']}")
            else:
                st.error("Complete all incident details.")

    with col2:
        st.subheader("Statutory Incident Ledger")
        if st.session_state.incidents_log:
            st.dataframe(pd.DataFrame(st.session_state.incidents_log), use_container_width=True)

# ------------------------------------------
# TAB 3: SPATIAL / EUDR VERIFIER
# ------------------------------------------
with tab_spatial:
    st.header("Spatial Coordinates & EUDR Verifier")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        lat = st.number_input("Latitude", value=-1.286389, format="%.6f")
        lon = st.number_input("Longitude", value=36.817223, format="%.6f")
        obs_date = st.date_input("Field Date", datetime.date.today())
        
        if st.button("Verify Spatial Compliance"):
            res = validate_spatial_compliance(lat, lon, str(obs_date))
            if res["valid"]:
                st.success("✅ SPATIAL PROOF VERIFIED")
                st.json(res)
            else:
                st.error(f"❌ {res['reason']}")

    with col2:
        st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=12)

# ------------------------------------------
# TAB 4: ASSURANCE READINESS ENGINE
# ------------------------------------------
with tab_readiness:
    st.header("IFRS S1 / S2 Assurance Readiness")
    vaulted_types = [doc["document_type"] for doc in st.session_state.evidence_vault]
    
    manifest = {
        "EMCA_NEMA_Permit": ("NEMA_EIA_LICENCE" in vaulted_types or "NEMA_ANNUAL_ENVIRONMENTAL_AUDIT" in vaulted_types),
        "DOSHS_WIBA_Compliance": ("DOSHS_SAFETY_INSPECTION_CERTIFICATE" in vaulted_types or "WIBA_INSURANCE_POLICY" in vaulted_types),
        "Minimum_Wage_Payroll_Audit": ("MINIMUM_WAGE_PAYROLL_REGISTER" in vaulted_types),
        "Board_E_and_S_Oversight": ("BOARD_MINUTES_ESG_OVERSIGHT" in vaulted_types)
    }
    
    evaluation = evaluate_esg_assurance_score(manifest)
    
    st.metric("Overall Readiness Score", f"{evaluation['score']}%")
    st.progress(evaluation['score'] / 100)
    st.info(evaluation['status'])
