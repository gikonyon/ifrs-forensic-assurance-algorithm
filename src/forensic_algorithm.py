"""
Forensic Assurance Algorithm
=============================
A system-agnostic, transaction-level verification engine for IFRS S1
(Governance) and IFRS S2 (Climate) disclosures.

Implements:
  1. IFRS S1 Governance Concentration & Parity Engine
  2. IFRS S2 Environmental Data Quality Score (DQS) Engine
  3. Assurance Risk Classification (Alpha - Zinc tiers)
  4. Forensic Report Generator

Author: Gikonyo Ndugu
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple
import json

# 1. IFRS S1 -- GOVERNANCE ENGINE
GENDER_PARITY_BASELINE: float = 0.50
MIN_HHI_AT_PARITY: float = 0.50

@dataclass
class BoardComposition:
    total_seats: int
    male_directors: int
    female_directors: int

    def __post_init__(self) -> None:
        if self.male_directors + self.female_directors != self.total_seats:
            raise ValueError("male_directors + female_directors must equal total_seats")
        if self.total_seats <= 0:
            raise ValueError("total_seats must be a positive integer")

@dataclass
class GovernanceResult:
    majority_share: float
    gender_share_gap: float
    hhi: float
    hhi_variance_pct: float
    kenyan_statutory_compliant: bool

def compute_governance_metrics(board: BoardComposition) -> GovernanceResult:
    s_male = board.male_directors / board.total_seats
    s_female = board.female_directors / board.total_seats
    majority_share = max(s_male, s_female)

    delta_g = abs(majority_share - GENDER_PARITY_BASELINE)
    hhi = (s_male ** 2) + (s_female ** 2)
    hhi_variance_pct = ((hhi - MIN_HHI_AT_PARITY) / MIN_HHI_AT_PARITY) * 100
    kenyan_compliant = majority_share <= (2 / 3) + 1e-9

    return GovernanceResult(
        majority_share=round(majority_share, 4),
        gender_share_gap=round(delta_g, 4),
        hhi=round(hhi, 4),
        hhi_variance_pct=round(hhi_variance_pct, 2),
        kenyan_statutory_compliant=kenyan_compliant,
    )

# 2. IFRS S2 -- DQS ENGINE
class DataMaturityTier(Enum):
    MANUAL_SPREADSHEETS = 0.00
    PERIODIC_BATCH_UPLOADS = 0.25
    AUTOMATED_ETL = 0.50
    DIRECT_API_INTEGRATION = 0.75
    IMMUTABLE_LEDGER = 1.00

DQS_WEIGHTS: Dict[str, float] = {
    "data_sourcing": 0.40,
    "spatial_temporal": 0.30,
    "ledger_immutability": 0.30,
}

@dataclass
class EmissionsInputs:
    scope_1: float
    scope_2: float
    total_output: float

    def intensity(self) -> float:
        if self.total_output <= 0:
            raise ValueError("total_output must be positive")
        return (self.scope_1 + self.scope_2) / self.total_output

@dataclass
class PipelineMaturity:
    data_sourcing: DataMaturityTier
    spatial_temporal: DataMaturityTier
    ledger_immutability: DataMaturityTier

@dataclass
class DQSResult:
    dqs: float
    classification: str
    components: Dict[str, float]

def compute_dqs(pipeline: PipelineMaturity) -> DQSResult:
    m_r = pipeline.data_sourcing.value
    g_t = pipeline.spatial_temporal.value
    a_v = pipeline.ledger_immutability.value

    dqs = (
        DQS_WEIGHTS["data_sourcing"] * m_r
        + DQS_WEIGHTS["spatial_temporal"] * g_t
        + DQS_WEIGHTS["ledger_immutability"] * a_v
    )
    dqs = round(dqs, 4)

    if dqs == 0.00:
        classification = "Unverified Narrative Asset"
    elif dqs < 0.40:
        classification = "Low-Assurance / Manual-Dominant Pipeline"
    elif dqs < 0.70:
        classification = "Partially Automated Pipeline"
    elif dqs < 1.00:
        classification = "High-Assurance Automated Pipeline"
    else:
        classification = "Continuous, Audit-Ready Assurance"

    return DQSResult(
        dqs=dqs,
        classification=classification,
        components={"M_r": m_r, "G_t": g_t, "A_v": a_v},
    )

# 3. ASSURANCE RISK CLASSIFICATION
RISK_TIERS: List[Tuple[str, float, float]] = [
    ("Alpha  (Audit-Ready)", 0.85, 1.01),
    ("Bravo  (Low Risk)", 0.65, 0.85),
    ("Charlie (Moderate Risk)", 0.45, 0.65),
    ("Delta  (Elevated Risk)", 0.25, 0.45),
    ("Zinc   (Critical / Unverified)", 0.00, 0.25),
]

def classify_assurance_risk(governance: GovernanceResult, dqs: DQSResult) -> str:
    governance_score = max(0.0, 1 - (governance.hhi_variance_pct / 100))
    combined = round((governance_score * 0.5) + (dqs.dqs * 0.5), 4)

    for label, lower, upper in RISK_TIERS:
        if lower <= combined < upper:
            return f"{label} -- combined score {combined}"
    return f"Unclassified -- combined score {combined}"

# 4. REPORT GENERATOR
def generate_forensic_report(
    entity_name: str,
    board: BoardComposition,
    emissions: EmissionsInputs,
    pipeline: PipelineMaturity,
) -> dict:
    governance = compute_governance_metrics(board)
    intensity = round(emissions.intensity(), 4)
    dqs_result = compute_dqs(pipeline)
    risk_tier = classify_assurance_risk(governance, dqs_result)

    return {
        "entity": entity_name,
        "ifrs_s1_governance": {
            "total_board_seats": board.total_seats,
            "male_directors": board.male_directors,
            "female_directors": board.female_directors,
            "majority_share": governance.majority_share,
            "gender_share_gap": governance.gender_share_gap,
            "hhi": governance.hhi,
            "hhi_variance_pct_above_parity_floor": governance.hhi_variance_pct,
            "kenyan_statutory_compliant": governance.kenyan_statutory_compliant,
        },
        "ifrs_s2_environmental": {
            "carbon_intensity_Ic": intensity,
            "pipeline_maturity": dqs_result.components,
            "data_quality_score": dqs_result.dqs,
            "classification": dqs_result.classification,
        },
        "assurance_classification": risk_tier,
    }

if __name__ == "__main__":
    kakuzi_board = BoardComposition(total_seats=8, male_directors=6, female_directors=2)
    kakuzi_emissions = EmissionsInputs(scope_1=0.0, scope_2=0.0, total_output=1.0)
    kakuzi_pipeline = PipelineMaturity(
        data_sourcing=DataMaturityTier.MANUAL_SPREADSHEETS,
        spatial_temporal=DataMaturityTier.MANUAL_SPREADSHEETS,
        ledger_immutability=DataMaturityTier.MANUAL_SPREADSHEETS,
    )

    report = generate_forensic_report(
        entity_name="Kakuzi PLC (Illustrative Baseline)",
        board=kakuzi_board,
        emissions=kakuzi_emissions,
        pipeline=kakuzi_pipeline,
    )

    print(json.dumps(report, indent=2))
