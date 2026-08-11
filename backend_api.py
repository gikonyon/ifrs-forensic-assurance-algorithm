from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import hashlib
import datetime

app = FastAPI(title="Uujuzi ESG Assurance Microservice", version="2.0")

class SpatialRequest(BaseModel):
    latitude: float
    longitude: float
    observation_date: str

class IncidentRequest(BaseModel):
    incident_type: str
    description: str
    employee_id: str

@app.post("/api/v1/vault/lock")
async def api_lock_evidence(issuer_id: str = Form(...), document_type: str = Form(...), file: UploadFile = File(...)):
    file_bytes = await file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    record = {
        "document_name": file.filename,
        "document_type": document_type,
        "issuer_id": issuer_id,
        "sha256_hash": file_hash,
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "audit_status": "LOCKED_FOR_ASSURANCE"
    }
    return {"status": "success", "data": record}

@app.post("/api/v1/verify-spatial")
def api_verify_spatial(req: SpatialRequest):
    is_in_kenya = (-4.7 <= req.latitude <= 5.5) and (33.9 <= req.longitude <= 41.9)
    if not is_in_kenya:
        raise HTTPException(status_code=400, detail="Location falls outside Kenyan jurisdiction boundaries.")
    return {"status": "success", "data": {"valid": True, "jurisdiction": "Kenya", "status": "EUDR / NEMA CLEAR"}}

@app.post("/api/v1/incidents/log")
def api_log_incident(req: IncidentRequest):
    sla_hours = 24 if req.incident_type.lower() == 'fatal' else 168
    deadline = datetime.datetime.utcnow() + datetime.timedelta(hours=sla_hours)
    return {
        "status": "success", 
        "data": {
            "employee_id": req.employee_id,
            "doshs_deadline": deadline.strftime("%Y-%m-%d %H:%M:%S UTC")
        }
    }
