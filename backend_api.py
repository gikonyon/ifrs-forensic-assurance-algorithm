import hashlib
import datetime
import json
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

app = FastAPI(
    title="Uujuzi ESG Assurance Microservice",
    description="REST API layer for real-economy regulatory verification and cryptographic evidence locking.",
    version="2.0.0"
)

# Request Models
class SpatialRequest(BaseModel):
    latitude: float
    longitude: float
    observation_date: str

class IncidentRequest(BaseModel):
    incident_type: str
    description: str
    employee_id: str

# API Endpoints
@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "Uujuzi ESG Assurance Engine",
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }

@app.post("/api/v1/vault/lock")
async def api_lock_evidence(
    issuer_id: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...)
):
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/verify-spatial")
def api_verify_spatial(req: SpatialRequest):
    # Coordinate Bounds Check for Kenya (-4.7 to 5.5 Lat, 33.9 to 41.9 Lon)
    is_in_kenya = (-4.7 <= req.latitude <= 5.5) and (33.9 <= req.longitude <= 41.9)
    
    try:
        obs_date = datetime.datetime.strptime(req.observation_date, "%Y-%m-%d").date()
        days_diff = (datetime.date.today() - obs_date).days
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    if not is_in_kenya:
        raise HTTPException(status_code=400, detail="Location falls outside Kenyan jurisdiction boundaries.")
    elif days_diff > 30:
        raise HTTPException(status_code=400, detail="Evidence stale. Field observation exceeds 30-day freshness SLA.")

    return {
        "status": "success",
        "data": {
            "valid": True,
            "latitude": req.latitude,
            "longitude": req.longitude,
            "observation_date": req.observation_date,
            "jurisdiction": "Kenya",
            "status": "EUDR / NEMA CLEAR"
        }
    }

@app.post("/api/v1/incidents/log")
def api_log_incident(req: IncidentRequest):
    inc_type = req.incident_type.lower()
    if inc_type not in ["fatal", "non_fatal"]:
        raise HTTPException(status_code=400, detail="Incident type must be 'fatal' or 'non_fatal'.")

    sla_hours = 24 if inc_type == "fatal" else 168
    timestamp = datetime.datetime.utcnow()
    deadline = timestamp + datetime.timedelta(hours=sla_hours)

    payload = {
        "employee_id": req.employee_id,
        "incident_type": req.incident_type.upper(),
        "logged_at": timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "doshs_deadline": deadline.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "description": req.description
    }
    payload["hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
    
    return {"status": "success", "data": payload}
