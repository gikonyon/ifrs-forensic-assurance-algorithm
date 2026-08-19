import hashlib
import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

# Single source of truth — see models/esg_forensic_engine.py. Previously this
# file re-implemented register_evidence_document / validate_spatial_compliance
# / the DOSHS SLA calculation inline, as a third copy alongside the versions
# test_assurance_engine.py expected to import and the engine module itself.
from models.esg_forensic_engine import (
    classify_assurance_document,
    check_assurance_coverage,
    detect_restatements,
    evaluate_esg_claim,
    register_evidence_document,
    validate_spatial_compliance,
    DOSHSIncidentTracker,
    evaluate_esg_assurance_score,
)

app = FastAPI(
    title="Uujuzi Forensic & ESG Assurance Engine API",
    description="Unified REST API layer for real-economy regulatory verification, cryptographic evidence vaulting, and ESG forensic analytics.",
    version="2.1.0",
)


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------
class SpatialRequest(BaseModel):
    latitude: float
    longitude: float
    observation_date: str


class IncidentRequest(BaseModel):
    incident_type: str
    description: str
    employee_id: str


class BankabilityRequest(BaseModel):
    manifest: dict


# ---------------------------------------------------------------------------
# Health & Status Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "Uujuzi Forensic & ESG Assurance Engine",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


# ---------------------------------------------------------------------------
# Cryptographic Evidence Vault Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/v1/vault/lock")
async def api_lock_evidence(
    issuer_id: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
):
    try:
        file_bytes = await file.read()
        record = register_evidence_document(file_bytes, file.filename, document_type, issuer_id)
        return {"status": "success", "data": record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Spatial & Jurisdiction Compliance Endpoints (EUDR / NEMA)
# ---------------------------------------------------------------------------
@app.post("/api/v1/verify-spatial")
def api_verify_spatial(req: SpatialRequest):
    result = validate_spatial_compliance(req.latitude, req.longitude, req.observation_date)
    if not result["valid"]:
        raise HTTPException(status_code=400, detail=result["reason"])
    return {"status": "success", "data": result}


# ---------------------------------------------------------------------------
# Workplace Incident Logging (DOSHS Compliance) Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/v1/incidents/log")
def api_log_incident(req: IncidentRequest):
    try:
        tracker = DOSHSIncidentTracker(req.incident_type, req.description, req.employee_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    incident_id = hashlib.sha256(
        f"{req.employee_id}{req.description}{datetime.datetime.now(datetime.timezone.utc)}".encode()
    ).hexdigest()[:10].upper()

    payload = tracker.generate_payload(incident_id)
    return {"status": "success", "data": payload}


# ---------------------------------------------------------------------------
# Bankability / ESG Assurance Scoring Endpoint
# ---------------------------------------------------------------------------
@app.post("/api/v1/bankability-score")
def api_bankability_score(req: BankabilityRequest):
    return {"status": "success", "data": evaluate_esg_assurance_score(req.manifest)}


# ---------------------------------------------------------------------------
# Forensic Engine & Assurance Tiering Endpoints
# ---------------------------------------------------------------------------
class ClassifyRequest(BaseModel):
    text: str
    filename: str = "document.pdf"


@app.post("/api/v1/classify-document")
def api_classify(req: ClassifyRequest):
    return classify_assurance_document(req.text, req.filename)


class CoverageRequest(BaseModel):
    documents: list  # [{"document_name": ..., "text": ...}, ...]


@app.post("/api/v1/check-coverage")
def api_check_coverage(req: CoverageRequest):
    return check_assurance_coverage(req.documents)


class RestatementRequest(BaseModel):
    text: str
    filename: str = "document.pdf"


@app.post("/api/v1/detect-restatements")
def api_detect_restatements(req: RestatementRequest):
    return detect_restatements(req.text, req.filename)


class ClaimRequest(BaseModel):
    entity_name: str
    claim_id: str
    category: str
    claimed_metric: str
    claim_year: int
    baseline_ndvi: float = 0.6
    current_ndvi: float = 0.4


@app.post("/api/v1/evaluate-claim")
def api_evaluate_claim(req: ClaimRequest):
    gis_data = {"baseline_ndvi": req.baseline_ndvi, "current_ndvi": req.current_ndvi}
    return evaluate_esg_claim(
        req.entity_name, req.claim_id, req.category, req.claimed_metric,
        req.claim_year, "Polygon()", gis_data,
    )
