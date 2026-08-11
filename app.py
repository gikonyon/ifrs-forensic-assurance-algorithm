import streamlit as st
import pandas as pd
import datetime
import hashlib
import json

# ==========================================
# 1. INLINE MODULES & COMPLIANCE LOGIC
# ==========================================

def register_evidence_document(file_bytes, document_name, document_type, issuer_accreditation_id):
    """
    Mints an immutable SHA-256 cryptographic hash for uploaded regulatory documents
    to ensure audit integrity for external assurance under IFRS S1/S2.
    """
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    document_record = {
        "document_name": document_name,
        "document_type": document_type,
        "issuer_id": issuer_accreditation_id,
        "sha256_hash": file_hash,
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "audit_status": "LOCKED_FOR_ASSURANCE"
    }
    return document_record


class DOSHSIncidentTracker:
    """
    Manages workplace health and safety incident logs and calculates
    statutory SLA deadlines under WIBA 2007 and OSHA 2007 guidelines.
    """
    def __init__(self, incident_type, description, employee_id):
        self.incident_type = incident_type.lower()  # 'fatal' or 'non_fatal'
        self.description = description
        self.employee_id = employee_id
        self.timestamp = datetime.datetime.utcnow()
        self.doshs_sla_deadline = self._calculate_sla()

    def _calculate_sla(self):
        # Statutory SLAs: Fatal = 24 Hours, Non-Fatal = 7 Days (168 Hours)
        sla_hours = 24 if self.incident_type == 'fatal' else 168
        return self.timestamp + datetime.timedelta(hours=sla_hours)

    def generate_payload(self, incident_id):
        payload = {
            "incident_id": incident_id,
            "employee_id": self.employee_id,
            "incident_type": self.incident_type.upper(),
            "logged_at": self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "doshs_deadline": self.doshs_sla_deadline.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "description": self.description
        }
        # Cryptographic payload verification hash
        payload["hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
        return payload


def validate_spatial_compliance(latitude, longitude, observation_date_str):
    """
    Validates field observation coordinates against Kenyan territorial bounds
    and enforces a 30-day freshness SLA for EUDR/NEMA deforestation evidence.
    """
    # Coordinate Bounds Check for Kenya (-4.7 to 5.5 Lat, 33.9 to 41.9 Lon)
    is_in_kenya = (-4.7 <= latitude <= 5.5) and (33.9 <= longitude <= 41.9)
    
    obs_date = datetime.datetime.strptime(observation_date_str, "%Y-%m-%d").date()
    days_diff = (datetime.date.today() - obs_date).days
    
    if not is_in_kenya:
        return {
            "valid": False,
            "reason": "Location falls outside Kenyan jurisdiction boundaries."
        }
    elif days_diff > 30:
        return {
            "valid": False,
            "reason": "Evidence stale. Field observation exceeds 30-day freshness SLA."
        }
    
    return {
        "valid": True,
        "latitude": latitude,
        "longitude": longitude,
        "observation_date": observation_date_str,
        "jurisdiction": "Kenya",
        "status": "EUDR / NEMA CLEAR"
    }


def evaluate_esg_assurance_score(evidence_manifest):
    """
    Calculates overall audit readiness based on vaulted evidence across 4 regulatory pillars.
    """
    required_pillars = {
        "EMCA_NEMA_Permit": 25,
        "DOSHS_WIBA_Compliance": 25,
        "Minimum_Wage_Payroll_Audit": 25,
        "Board_E_and_S_Oversight": 25
    }
    
    score = 0
    for pillar, points in required_pillars.items():
        if evidence_manifest.get(pillar, False):
            score += points

    if score >= 75:
        status = "🟢 BANKABLE / AUDIT-READY — Evidence satisfies CBK, NEMA, and IFC standards."
    elif score >= 50:
        status = "🟡 MODERATE ASSURANCE RISK — Additional evidence files required prior to external audit."
    else:
        status = "🔴 UNBANKABLE / HIGH ASSURANCE RISK — Critical compliance evidence missing."

    return {
        "score": score,
        "status": status
    }


# ==========================================
# 2. STREAMLIT UI & INTERFACE ENGINE
# ==========================================

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

st.sidebar.markdown("---")
st.sidebar.info("""
**Regulatory Frameworks Applied:**
- IFC & NEMA 2025 Real Sector Guidelines
- EMCA Cap 387 / EIA Regulations
- OSHA 2007 & WIBA 2007 (DOSHS)
- IFRS S1 / S2 & CBK Green Taxonomy
""")

st.title("UUJUZI ESG EVIDENCE & FORENSIC ASSURANCE LAYER")
st.caption(f"Real-Economy Compliance Engine | Active Focus: {target_sector}")

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
    st.caption("Upload regulatory permits, EIA audits, labor registers, or OSH policies to mint an immutable SHA-256 hash.")
    
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
        else:
            st.info("No evidence documents vaulted in current session.")

# ------------------------------------------
# TAB 2: DOSHS / WIBA INCIDENTS
# ------------------------------------------
with tab_doshs:
    st.header("DOSHS / WIBA Workplace Incident Engine")
    st.caption("Enforces statutory SLA counters for DOSHS reporting under WIBA 2007 (Fatal = 24hrs, Non-Fatal = 7 Days).")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        inc_type = st.radio("Severity Level", ["non_fatal", "fatal"])
        emp_id = st.text_input("Employee Identifier / Personnel ID")
        desc = st.text_area("Incident Summary & Nature of Injury")
        
        if st.button("Log Incident & Calculate SLA"):
            if emp_id and desc:
                tracker = DOSHSIncidentTracker(inc_type, desc, emp_id)
                inc_id = f"INC-{len(st.session_state.incidents_log)+1:03d}"
                payload = tracker.generate_payload(inc_id)
                st.session_state.incidents_log.append(payload)
                st.warning(f"Incident Logged. Legal DOSHS-1 Deadline: {payload['doshs_deadline']}")
            else:
                st.error("Please complete all incident details.")

    with col2:
        st.subheader("Statutory Compliance Incident Ledger")
        if st.session_state.incidents_log:
            st.dataframe(pd.DataFrame(st.session_state.incidents_log), use_container_width=True)
        else:
            st.info("Zero workplace incidents currently logged.")

# ------------------------------------------
# TAB 3: SPATIAL / EUDR VERIFIER
# ------------------------------------------
with tab_spatial:
    st.header("Geospatial & EUDR Deforestation Validator")
    st.caption("Verifies field coordinates against Kenyan boundaries and enforces 30-day freshness SLAs.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        lat = st.number_input("Latitude", value=-1.286389, format="%.6f")
        lon = st.number_input("Longitude", value=36.817223, format="%.6f")
        obs_date = st.date_input("Field Observation Date", datetime.date.today())
        
        if st.button("Verify Spatial Compliance"):
            res = validate_spatial_compliance(lat, lon, str(obs_date))
            if res["valid"]:
                st.success("✅ SPATIAL PROOF VERIFIED")
                st.json(res)
            else:
                st.error(f"❌ {res['reason']}")

    with col2:
        st.subheader("Field Observation Location")
        st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=12)

# ------------------------------------------
# TAB 4: ASSURANCE READINESS ENGINE
# ------------------------------------------
with tab_readiness:
    st.header("IFRS S1 / S2 & Real Sector Audit Readiness")
    st.caption("Evaluates overall bankability based on evidence locked in the Cryptographic Vault.")
    
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
    
    if evaluation['score'] >= 75:
        st.success(evaluation['status'])
    elif evaluation['score'] >= 50:
        st.warning(evaluation['status'])
    else:
        st.error(evaluation['status'])
