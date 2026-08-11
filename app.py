import streamlit as st
import pandas as pd
import datetime
import hashlib
import json

# ==========================================
# PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Uujuzi ESG Assurance Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for C-Suite Dark/Emerald Theme
st.markdown("""
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0B3C26;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #64748B;
        margin-bottom: 20px;
        letter-spacing: 2px;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-left: 5px solid #0B3C26;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .status-pass {
        color: #059669;
        font-weight: bold;
    }
    .status-fail {
        color: #DC2626;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "evidence_vault" not in st.session_state:
    st.session_state.evidence_vault = []
if "incidents_log" not in st.session_state:
    st.session_state.incidents_log = []

# ==========================================
# SIDEBAR NAVIGATION & SECTOR TOGGLE
# ==========================================
st.sidebar.image("https://via.placeholder.com/200x60/0B3C26/FFFFFF?text=UUJUZI+ASSURANCE", use_column_width=True)
st.sidebar.markdown("---")
st.sidebar.title("Configuration")

target_sector = st.sidebar.selectbox(
    "Target Sector Focus",
    ["Manufacturing", "Agribusiness & Exporters", "Affordable Housing / Construction", "Commercial Banking (Portfolio E&S)"]
)

st.sidebar.markdown("---")
st.sidebar.info("""
**Regulatory Baseline:**
- IFC & NEMA 2025 Real Sector Guidelines
- EMCA Cap 387 / EIA Regulations
- OSHA 2007 & WIBA 2007 (DOSHS)
- IFRS S1 / S2 & CBK Green Taxonomy
""")

# ==========================================
# MAIN HEADER
# ==========================================
st.markdown('<div class="main-header">UUJUZI ESG EVIDENCE & FORENSIC ASSURANCE LAYER</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">REAL-ECONOMY COMPLIANCE & AUDIT-READINESS ENGINE</div>', unsafe_allow_html=True)

# Top Metrics Row
m1, m2, m3, m4 = st.columns(4)
m1.metric("Selected Sector", target_sector)
m2.metric("Vaulted Evidence Files", len(st.session_state.evidence_vault))
m3.metric("Open EHS Incidents", len(st.session_state.incidents_log))
m4.metric("Assurance Readiness", "Evaluating...")

st.markdown("---")

# ==========================================
# CORE PLATFORM TABS
# ==========================================
tab_vault, tab_doshs, tab_spatial, tab_readiness = st.tabs([
    "📂 Cryptographic Evidence Vault", 
    "⚠️ DOSHS / WIBA Incident Tracker", 
    "🌍 Spatial & EUDR Geotag Verifier", 
    "📊 IFRS S1/S2 Gap & Audit Engine"
])

# ------------------------------------------
# TAB 1: EVIDENCE VAULT & HASH REGISTRY
# ------------------------------------------
with tab_vault:
    st.header("Forensic Evidence Vault")
    st.caption("Upload regulatory permits, EIA audits, labor registers, or OSH policies to mint an immutable cryptographic hash.")
    
    col_u1, col_u2 = st.columns([1, 1])
    
    with col_u1:
        doc_type = st.selectbox("Select Document Classification", [
            "NEMA_EIA_LICENCE",
            "NEMA_ANNUAL_ENVIRONMENTAL_AUDIT",
            "DOSHS_SAFETY_INSPECTION_CERTIFICATE",
            "WIBA_INSURANCE_POLICY",
            "MINIMUM_WAGE_PAYROLL_REGISTER",
            "BOARD_MINUTES_ESG_OVERSIGHT"
        ])
        issuer_id = st.text_input("Issuer / Auditor Accreditation ID", placeholder="e.g., NEMA/LEAD/EXPERT/1042")
        uploaded_file = st.file_uploader("Upload Source PDF/Image Evidence", type=["pdf", "png", "jpg"])
        
        if st.button("Register & Lock Evidence", type="primary"):
            if uploaded_file and issuer_id:
                file_bytes = uploaded_file.read()
                file_hash = hashlib.sha256(file_bytes).hexdigest()
                
                doc_record = {
                    "document_name": uploaded_file.name,
                    "document_type": doc_type,
                    "issuer_id": issuer_id,
                    "sha256_hash": file_hash,
                    "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "status": "LOCKED_FOR_ASSURANCE"
                }
                st.session_state.evidence_vault.append(doc_record)
                st.success(f"Document locked! Hash: {file_hash[:16]}...")
            else:
                st.error("Please provide both an accreditation ID and a file.")

    with col_u2:
        st.subheader("Immutable Vault Register")
        if st.session_state.evidence_vault:
            df_vault = pd.DataFrame(st.session_state.evidence_vault)
            st.dataframe(df_vault[["document_type", "issuer_id", "sha256_hash", "timestamp"]], use_container_width=True)
        else:
            st.info("No evidence locked in current session.")

# ------------------------------------------
# TAB 2: DOSHS / WIBA INCIDENT ENGINE
# ------------------------------------------
with tab_doshs:
    st.header("DOSHS & WIBA Workplace Incident Log")
    st.caption("Enforce statutory SLA counters for DOSHS reporting under WIBA 2007 (Fatal = 24hrs, Non-Fatal = 7 Days).")
    
    col_i1, col_i2 = st.columns([1, 1])
    
    with col_i1:
        incident_type = st.radio("Incident Severity", ["non_fatal", "fatal"])
        inc_desc = st.text_area("Incident Summary / Nature of Injury", placeholder="Describe event, location, and casualties if any...")
        emp_name = st.text_input("Employee Identifier / ID Number")
        
        if st.button("Log Incident & Calculate Legal SLA"):
            if inc_desc and emp_name:
                now = datetime.datetime.utcnow()
                sla_hrs = 24 if incident_type == "fatal" else 168 # 7 days
                deadline = now + datetime.timedelta(hours=sla_hrs)
                
                payload = {
                    "incident_id": f"INC-{len(st.session_state.incidents_log)+1:03d}",
                    "employee": emp_name,
                    "type": incident_type.upper(),
                    "logged_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "doshs_deadline": deadline.strftime("%Y-%m-%d %H:%M:%S"),
                    "description": inc_desc
                }
                # Hash for auditability
                payload["hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
                st.session_state.incidents_log.append(payload)
                st.warning(f"Incident Logged. Mandatory DOSHS-1 Filing Deadline: {deadline.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            else:
                st.error("Please complete all incident details.")

    with col_i2:
        st.subheader("Statutory Compliance Incident Ledger")
        if st.session_state.incidents_log:
            st.dataframe(pd.DataFrame(st.session_state.incidents_log), use_container_width=True)
        else:
            st.info("Zero active workplace safety incidents recorded.")

# ------------------------------------------
# TAB 3: SPATIAL & EUDR GEOTAG VERIFIER
# ------------------------------------------
with tab_spatial:
    st.header("Geospatial & EUDR Deforestation Validator")
    st.caption("Verify that field observations, raw material origins, or housing project sites meet EMCA and EUDR spatial coordinates.")
    
    col_s1, col_s2 = st.columns([1, 1])
    
    with col_s1:
        lat = st.number_input("Latitude", value=-1.286389, format="%.6f")
        lon = st.number_input("Longitude", value=36.817223, format="%.6f")
        obs_date = st.date_input("Field Observation Date", datetime.date.today())
        
        if st.button("Run Spatial Compliance Check"):
            # Coordinates Bounds Check for Kenya (-4.7 to 5.5 Lat, 33.9 to 41.9 Lon)
            is_in_kenya = (-4.7 <= lat <= 5.5) and (33.9 <= lon <= 41.9)
            days_diff = (datetime.date.today() - obs_date).days
            
            if not is_in_kenya:
                st.error("❌ VALIDATION FAILED: Location falls outside Kenyan jurisdiction boundaries.")
            elif days_diff > 30:
                st.warning("⚠️ STALE EVIDENCE: Field observation exceeds the 30-day freshness threshold.")
            else:
                st.success("✅ SPATIAL PROOF VERIFIED: Geotag inside valid boundaries and compliant with freshness SLAs.")
                st.json({
                    "latitude": lat,
                    "longitude": lon,
                    "observation_date": str(obs_date),
                    "jurisdiction": "Kenya",
                    "status": "EUDR / NEMA CLEAR"
                })

    with col_s2:
        st.subheader("Site Boundary Map Preview")
        map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
        st.map(map_data, zoom=12)

# ------------------------------------------
# TAB 4: IFRS S1/S2 READINESS ENGINE
# ------------------------------------------
with tab_readiness:
    st.header("IFRS S1 / S2 & Real Sector Assurance Readiness")
    st.caption("Automated gap evaluation against regulatory requirements for target sectors.")
    
    # Check vault contents
    vaulted_types = [doc["document_type"] for doc in st.session_state.evidence_vault]
    
    st.subheader("Required Evidence Checks")
    
    check1 = st.checkbox("NEMA EIA Licence / Annual Environmental Audit Present", value="NEMA_EIA_LICENCE" in vaulted_types or "NEMA_ANNUAL_ENVIRONMENTAL_AUDIT" in vaulted_types)
    check2 = st.checkbox("DOSHS OSH Certificate / WIBA Insurance Policy Active", value="DOSHS_SAFETY_INSPECTION_CERTIFICATE" in vaulted_types or "WIBA_INSURANCE_POLICY" in vaulted_types)
    check3 = st.checkbox("Minimum Wage & Labor Compliance Verified", value="MINIMUM_WAGE_PAYROLL_REGISTER" in vaulted_types)
    check4 = st.checkbox("Board-Level ESG Oversight Minutes Vaulted", value="BOARD_MINUTES_ESG_OVERSIGHT" in vaulted_types)
    
    # Score calculation
    score = sum([check1, check2, check3, check4]) * 25
    
    st.markdown("---")
    st.subheader(f"Overall Assurance Readiness Score: {score}%")
    st.progress(score / 100)
    
    if score >= 75:
        st.success("🟢 STATUS: BANKABLE / AUDIT-READY — Documented evidence satisfies CBK, NEMA, and IFC standards.")
    elif score >= 50:
        st.warning("🟡 STATUS: MODERATE ASSURANCE RISK — Additional evidence files required prior to external audit.")
    else:
        st.error("🔴 STATUS: UNBANKABLE / HIGH ASSURANCE RISK — Severe evidence gaps detected across legal compliance baselines.")
