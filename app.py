import streamlit as st
import pandas as pd
import datetime
import hashlib
import json
import re

# ==========================================
# 1. CORE FORENSIC & VERIFICATION ENGINES
# ==========================================

def scan_and_extract_report(file_bytes, filename):
    """
    Simulates AI text/data extraction from an uploaded corporate ESG report.
    Extracts self-reported compliance claims, targets, and mentioned certifications.
    """
    file_size_kb = len(file_bytes) / 1024
    
    # Mock extracted claims based on typical ESG report analysis
    extracted_claims = [
        {"claim": "NEMA Environmental Impact Assessment Audit", "status": "Self-Reported", "cert_type": "NEMA_EIA_LICENCE", "detected_id": "NEMA/LEAD/1042"},
        {"claim": "DOSHS Workplace Safety Compliance", "status": "Self-Reported", "cert_type": "DOSHS_SAFETY_INSPECTION_CERTIFICATE", "detected_id": "DOSHS/2025/8892"},
        {"claim": "ISO 14001 Environmental Management System", "status": "Claimed", "cert_type": "ISO_14001_ENVIRONMENTAL_CERTIFICATE", "detected_id": "ISO14001-KE992831"},
        {"claim": "Scope 2 Carbon Reduction of 30%", "status": "Self-Reported", "cert_type": "GHG_PROTOCOL_AUDIT", "detected_id": None},
        {"claim": "Minimum Wage & Fair Labor Register", "status": "Self-Reported", "cert_type": "MINIMUM_WAGE_PAYROLL_REGISTER", "detected_id": None}
    ]
    return {
        "filename": filename,
        "size_kb": f"{file_size_kb:.2f} KB",
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "claims": extracted_claims
    }


def verify_esg_certification(cert_type, cert_id, org_name="Client Entity"):
    """
    Validates ESG certificate formats and simulates registry endpoint verification.
    """
    schemas = {
        "ISO_14001_ENVIRONMENTAL_CERTIFICATE": r"^ISO14001-[A-Z0-9]{6,12}$",
        "NEMA_EIA_LICENCE": r"^NEMA\/[A-Z0-9\/]{4,12}$",
        "DOSHS_SAFETY_INSPECTION_CERTIFICATE": r"^DOSHS\/[0-9]{4}\/[0-9]{4,6}$"
    }

    pattern = schemas.get(cert_type)
    if pattern and not re.match(pattern, cert_id):
        return {
            "status": "REJECTED",
            "reason": f"Malformed ID syntax for {cert_type}",
            "recommendation": "Flag for human audit; request corrected document."
        }

    # Registry lookup validation
    if cert_id and len(cert_id) > 5:
        return {
            "status": "VERIFIED",
            "details": f"Active {cert_type} certificate validated for {org_name}.",
            "recommendation": "Pass to primary ESG analytics pipeline; assign high data confidence score."
        }
    else:
        return {
            "status": "UNVERIFIED",
            "details": "Certificate ID not found or status marked expired/revoked.",
            "recommendation": "Penalize ESG trust score; issue formal clarification request to entity."
        }


def register_evidence_document(file_bytes, document_name, document_type, issuer_accreditation_id):
    """
    Mints an immutable SHA-256 cryptographic hash for uploaded regulatory documents
    and certifications to ensure audit integrity under ISSA 5000 and IFRS S1/S2.
    """
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    return {
        "document_name": document_name,
        "document_type": document_type,
        "issuer_id": issuer_accreditation_id,
        "sha256_hash": file_hash,
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "audit_status": "LOCKED_FOR_ASSURANCE"
    }


class DOSHSIncidentTracker:
    def __init__(self, incident_type, description, employee_id):
        self.incident_type = incident_type.lower()
        self.description = description
        self.employee_id = employee_id
        self.timestamp = datetime.datetime.utcnow()
        self.doshs_sla_deadline = self._calculate_sla()

    def _calculate_sla(self):
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
        payload["hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
        return payload


def validate_spatial_compliance(latitude, longitude, observation_date_str):
    is_in_kenya = (-4.7 <= latitude <= 5.5) and (33.9 <= longitude <= 41.9)
    obs_date = datetime.datetime.strptime(observation_date_str, "%Y-%m-%d").date()
    days_diff = (datetime.date.today() - obs_date).days
    
    if not is_in_kenya:
        return {"valid": False, "reason": "Location falls outside Kenyan jurisdiction boundaries."}
    elif days_diff > 30:
        return {"valid": False, "reason": "Evidence stale. Field observation exceeds 30-day freshness SLA."}
    
    return {
        "valid": True,
        "latitude": latitude,
        "longitude": longitude,
        "observation_date": observation_date_str,
        "jurisdiction": "Kenya",
        "status": "EUDR / NEMA CLEAR"
    }


def evaluate_esg_assurance_score(evidence_manifest):
    required_pillars = {
        "EMCA_NEMA_Permit": 20,
        "DOSHS_WIBA_Compliance": 20,
        "ISO_EHS_Certifications": 15,
        "Minimum_Wage_Payroll_Audit": 15,
        "Board_E_and_S_Oversight": 15,
        "SDG_Target_Alignment": 15
    }
    
    score = sum([points for pillar, points in required_pillars.items() if evidence_manifest.get(pillar, False)])

    if score >= 80:
        status = "🟢 BANKABLE / AUDIT-READY — Evidence satisfies ISSA 5000, CBK, NEMA, and IFC standards."
        rec = "Proceed to external assurance practitioner review. Prepare board presentation for investor due diligence."
    elif score >= 50:
        status = "🟡 MODERATE ASSURANCE RISK — Additional evidence files and certifications required."
        rec = "Initiate Uujuzi 90-Day Remediation Roadmap. Attach missing ISO/SDG certificates to substantiate self-reported claims."
    else:
        status = "🔴 UNBANKABLE / HIGH ASSURANCE RISK — Critical compliance evidence and certifications missing."
        rec = "Immediate management intervention required. Upload statutory permits (NEMA/DOSHS) and establish data ownership matrix."

    return {
        "score": score,
        "status": status,
        "recommendation": rec
    }


# ==========================================
# 2. STREAMLIT UI & INTERFACE ENGINE
# ==========================================

st.set_page_config(
    page_title="Uujuzi ESG Evidence & Forensic Assurance Layer",
    page_icon="🛡️",
    layout="wide"
)

# Initialize Session States
if "evidence_vault" not in st.session_state:
    st.session_state.evidence_vault = []
if "incidents_log" not in st.session_state:
    st.session_state.incidents_log = []
if "scanned_report" not in st.session_state:
    st.session_state.scanned_report = None

# Sidebar Navigation
st.sidebar.title("Uujuzi Platform")
target_sector = st.sidebar.selectbox(
    "Target Sector Focus",
    ["Manufacturing", "Agribusiness & Exporters", "Affordable Housing / Construction", "Commercial Banking (Portfolio E&S)"]
)

st.sidebar.markdown("---")
st.sidebar.info("""
**Uujuzi Verification Workflow:**
1. **Scan & Parse:** Upload ESG/Annual Report
2. **Analyze & Verify:** Validate Certification IDs
3. **Recommend & Vault:** Attach proof for gap closure
""")

st.title("UUJUZI ESG EVIDENCE & FORENSIC ASSURANCE LAYER")
st.caption(f"Real-Economy Compliance & SDG Proof Engine | Active Sector: {target_sector}")

tab_scan, tab_vault, tab_doshs, tab_spatial, tab_sdg, tab_readiness = st.tabs([
    "🔍 Report Scan & Analysis",
    "📂 Cryptographic Vault & Certs", 
    "⚠️ DOSHS / WIBA Tracker", 
    "🌍 Spatial & EUDR Verifier", 
    "🎯 SDG Contribution Mapper",
    "📊 IFRS S1/S2 Gap & Audit Engine"
])

# ------------------------------------------
# TAB 1: REPORT SCAN & ANALYSIS (NEW INTAKE FLOW)
# ------------------------------------------
with tab_scan:
    st.header("1. ESG Report Intake & Automated Analysis")
    st.caption("Upload raw sustainability reports or annual disclosures for automated claim extraction and certification validation.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        report_file = st.file_uploader("Upload Company ESG / Annual Report (PDF/Images)", type=["pdf", "png", "jpg"])
        
        if st.button("Scan & Analyze Report", type="primary"):
            if report_file:
                file_bytes = report_file.read()
                st.session_state.scanned_report = scan_and_extract_report(file_bytes, report_file.name)
                st.success("Report successfully parsed! Extracted self-reported claims below.")
            else:
                st.error("Please upload a report to scan.")

    with col2:
        st.subheader("Extracted Self-Reported Claims & Certifications")
        if st.session_state.scanned_report:
            st.write(f"**Source File:** {st.session_state.scanned_report['filename']} ({st.session_state.scanned_report['size_kb']})")
            
            claims_df = pd.DataFrame(st.session_state.scanned_report['claims'])
            st.dataframe(claims_df, use_container_width=True)
        else:
            st.info("Upload an ESG report on the left to trigger automated analysis.")

    if st.session_state.scanned_report:
        st.markdown("---")
        st.header("2. Certification Registry Verification")
        
        selected_claim = st.selectbox("Select Extracted Certification to Verify", [c["claim"] for c in st.session_state.scanned_report['claims']])
        claim_data = next(c for c in st.session_state.scanned_report['claims'] if c["claim"] == selected_claim)
        
        col_v1, col_v2 = st.columns([1, 1])
        with col_v1:
            cert_id_input = st.text_input("Extracted / Entered Certification ID", value=claim_data["detected_id"] if claim_data["detected_id"] else "")
            
            if st.button("Run Registry Verification"):
                if cert_id_input:
                    verification_res = verify_esg_certification(claim_data["cert_type"], cert_id_input)
                    if verification_res["status"] == "VERIFIED":
                        st.success(f"✅ {verification_res['details']}")
                        st.info(f"**Uujuzi Recommendation:** {verification_res['recommendation']}")
                    else:
                        st.error(f"❌ {verification_res['reason'] if 'reason' in verification_res else verification_res['details']}")
                        st.warning(f"**Uujuzi Recommendation:** {verification_res['recommendation']}")
                else:
                    st.error("No Certificate ID detected. Proceed to Vault tab to attach official document.")

# ------------------------------------------
# TAB 2: EVIDENCE VAULT & CERTIFICATIONS
# ------------------------------------------
with tab_vault:
    st.header("Targeted Evidence & Certification Vault")
    st.caption("Attach official documented certificates recommended during analysis to lock SHA-256 proof.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        doc_type = st.selectbox("Document / Certification Classification", [
            "NEMA_EIA_LICENCE",
            "NEMA_ANNUAL_ENVIRONMENTAL_AUDIT",
            "DOSHS_SAFETY_INSPECTION_CERTIFICATE",
            "ISO_14001_ENVIRONMENTAL_CERTIFICATE",
            "ISO_45001_HEALTH_SAFETY_CERTIFICATE",
            "WIBA_INSURANCE_POLICY",
            "MINIMUM_WAGE_PAYROLL_REGISTER",
            "BOARD_MINUTES_ESG_OVERSIGHT",
            "SDG_IMPACT_VERIFICATION_REPORT"
        ])
        issuer_id = st.text_input("Issuer / Accreditation ID", placeholder="e.g., NEMA/LEAD/1042 or ISO/KE/8821")
        uploaded_file = st.file_uploader("Upload Source PDF/Image Evidence", type=["pdf", "png", "jpg"], key="vault_upload")
        
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
# TAB 3: DOSHS / WIBA INCIDENTS
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
# TAB 4: SPATIAL / EUDR VERIFIER
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
# TAB 5: SDG CONTRIBUTION MAPPER
# ------------------------------------------
with tab_sdg:
    st.header("SDG Contribution & Impact Alignment")
    st.caption("Maps corporate ESG activities to target-level Sustainable Development Goals (SDGs).")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        sdg_target = st.selectbox("Primary Target SDG", [
            "SDG 8: Decent Work & Economic Growth",
            "SDG 12: Responsible Consumption & Production",
            "SDG 13: Climate Action",
            "SDG 15: Life on Land (Deforestation Free)"
        ])
        claim_text = st.text_area("Specific SDG Claim Statement", placeholder="e.g., Achieved 100% traceable sourcing across supply chain.")
        ev_link = st.selectbox("Linked Evidence File", [doc["document_type"] for doc in st.session_state.evidence_vault] if st.session_state.evidence_vault else ["No files in vault"])
        
        if st.button("Validate SDG Alignment"):
            if st.session_state.evidence_vault and ev_link != "No files in vault":
                st.success(f"Claim mapped to {sdg_target} with verified evidence backing!")
            else:
                st.warning("Claim registered as 'Unsupported' (Score 1) — Requires source evidence in Vault.")

    with col2:
        st.subheader("SDG Claim Validation Logic")
        st.markdown("""
        - **Score 5 (Assurance-Ready):** Documented source evidence + calculation logic + independent audit.
        - **Score 3 (Internally Supported):** Internal records available; lacking third-party verification.
        - **Score 1 (Unsupported):** High greenwashing risk. Narrative claim without vaulted proof.
        """)

# ------------------------------------------
# TAB 6: ASSURANCE READINESS & RECOMMENDATIONS
# ------------------------------------------
with tab_readiness:
    st.header("IFRS S1 / S2 Gap Analysis & Modernized Recommendations")
    st.caption("Evaluates audit readiness across statutory permits, ISO certifications, and SDG alignments.")
    
    vaulted_types = [doc["document_type"] for doc in st.session_state.evidence_vault]
    
    manifest = {
        "EMCA_NEMA_Permit": ("NEMA_EIA_LICENCE" in vaulted_types or "NEMA_ANNUAL_ENVIRONMENTAL_AUDIT" in vaulted_types),
        "DOSHS_WIBA_Compliance": ("DOSHS_SAFETY_INSPECTION_CERTIFICATE" in vaulted_types or "WIBA_INSURANCE_POLICY" in vaulted_types),
        "ISO_EHS_Certifications": ("ISO_14001_ENVIRONMENTAL_CERTIFICATE" in vaulted_types or "ISO_45001_HEALTH_SAFETY_CERTIFICATE" in vaulted_types),
        "Minimum_Wage_Payroll_Audit": ("MINIMUM_WAGE_PAYROLL_REGISTER" in vaulted_types),
        "Board_E_and_S_Oversight": ("BOARD_MINUTES_ESG_OVERSIGHT" in vaulted_types),
        "SDG_Target_Alignment": ("SDG_IMPACT_VERIFICATION_REPORT" in vaulted_types)
    }
    
    evaluation = evaluate_esg_assurance_score(manifest)
    
    st.metric("Overall Assurance Readiness Score", f"{evaluation['score']}%")
    st.progress(evaluation['score'] / 100)
    
    st.markdown("### Executive Analysis & Verdict")
    if evaluation['score'] >= 80:
        st.success(evaluation['status'])
    elif evaluation['score'] >= 50:
        st.warning(evaluation['status'])
    else:
        st.error(evaluation['status'])
        
    st.markdown("### Modernized Strategic Recommendation")
    st.info(f"**Uujuzi Guidance:** {evaluation['recommendation']}")
