#!/usr/bin/env python3
"""
IFRS Forensic Assurance Algorithm
---------------------------------

Research-grade, dependency-free reference implementation for analytical
verification of selected sustainability disclosures relevant to IFRS S1/S2.

This is a research prototype. It is NOT an audit opinion, assurance opinion,
legal interpretation of IFRS, or substitute for professional judgement.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_PARITY_BENCHMARK = 0.50

RISK_STATES = [
    "ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON",
    "ZETA", "ETA", "THETA", "IOTA", "KAPPA",
    "LAMBDA", "MU", "NU", "XI", "OMICRON",
    "PI", "RHO", "SIGMA", "TAU", "UPSILON",
    "PHI", "CHI", "PSI", "OMEGA", "ZINC",
]

# Higher score = stronger assurance readiness.
# The 25 states are intentionally research-specific and are not IFRS labels.
RISK_THRESHOLDS = [
    (96, "ALPHA"),
    (92, "BETA"),
    (88, "GAMMA"),
    (84, "DELTA"),
    (80, "EPSILON"),
    (76, "ZETA"),
    (72, "ETA"),
    (68, "THETA"),
    (64, "IOTA"),
    (60, "KAPPA"),
    (56, "LAMBDA"),
    (52, "MU"),
    (48, "NU"),
    (44, "XI"),
    (40, "OMICRON"),
    (36, "PI"),
    (32, "RHO"),
    (28, "SIGMA"),
    (24, "TAU"),
    (20, "UPSILON"),
    (16, "PHI"),
    (12, "CHI"),
    (8, "PSI"),
    (4, "OMEGA"),
    (0, "ZINC"),
]


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def safe_percentage(numerator: float, denominator: float) -> Optional[float]:
    if denominator == 0:
        return None
    return (numerator / denominator) * 100.0


def round_or_none(value: Optional[float], digits: int = 4) -> Optional[float]:
    return None if value is None else round(value, digits)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hash(value: Any) -> str:
    payload = canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class GovernanceResult:
    male_share: float
    female_share: float
    parity_benchmark: float
    gender_share_gap: float
    hhi: float
    parity_hhi: float
    hhi_excess: float
    two_thirds_threshold: float
    female_meets_two_thirds: bool
    governance_integrity_score: float
    governance_risk: str


@dataclass
class ClimateResult:
    scope1_tco2e: float
    scope2_tco2e: float
    total_scope1_scope2_tco2e: float
    total_output: float
    intensity: Optional[float]
    unit: str
    arithmetic_valid: bool


@dataclass
class DataQualityResult:
    source_integrity: float
    traceability: float
    completeness: float
    consistency: float
    verification: float
    weights: Dict[str, float]
    score: float
    tier: str


@dataclass
class VerificationResult:
    verification_id: str
    metric: str
    reported_value: Optional[float]
    recalculated_value: Optional[float]
    variance: Optional[float]
    variance_percentage: Optional[float]
    tolerance_percentage: float
    source_exists: bool
    evidence_exists: bool
    arithmetic_match: bool
    status: str
    exception_code: Optional[str]
    exception_message: Optional[str]
    timestamp: str


@dataclass
class EvidenceRecord:
    source_id: str
    source_type: str
    description: str
    value: Optional[float] = None
    document_hash: Optional[str] = None
    transaction_id: Optional[str] = None
    verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LineageNode:
    node_id: str
    node_type: str
    description: str
    parent_ids: List[str] = field(default_factory=list)
    hash: Optional[str] = None


@dataclass
class AssuranceResult:
    governance_score: float
    climate_data_quality_score: float
    traceability_score: float
    verification_score: float
    exception_integrity_score: float
    forensic_assurance_index: float
    assurance_state: str
    risk_level: str
    drivers: List[str]


@dataclass
class DiagnosticReport:
    entity: str
    reporting_period: str
    generated_at: str
    governance: GovernanceResult
    climate: ClimateResult
    data_quality: DataQualityResult
    verification_results: List[VerificationResult]
    assurance: AssuranceResult
    lineage: List[LineageNode]
    exceptions: List[VerificationResult]


# ---------------------------------------------------------------------------
# IFRS S1 Governance Engine
# ---------------------------------------------------------------------------

def gender_share_gap(
    female_share: float,
    benchmark: float = DEFAULT_PARITY_BENCHMARK,
) -> float:
    """Absolute gap between observed female share and analytical benchmark."""
    if not 0 <= female_share <= 1:
        raise ValueError("female_share must be between 0 and 1.")
    if not 0 <= benchmark <= 1:
        raise ValueError("benchmark must be between 0 and 1.")
    return abs(female_share - benchmark)


def hhi(shares: Sequence[float]) -> float:
    """
    Conventional HHI on decimal shares.

    Example:
        [0.50, 0.50] -> 0.50
        [1.00, 0.00] -> 1.00

    The result is on a 0-1 scale, not the conventional 0-10,000 scale.
    """
    if not shares:
        raise ValueError("At least one share is required.")
    if any(s < 0 for s in shares):
        raise ValueError("Shares cannot be negative.")
    total = sum(shares)
    if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError(f"Shares must sum to 1.0; received {total}.")
    return sum(s * s for s in shares)


def governance_integrity_score(
    female_share: float,
    hhi_value: float,
    parity_benchmark: float = DEFAULT_PARITY_BENCHMARK,
) -> float:
    """
    Research-specific governance score.

    50% of the score comes from gender-gap proximity to the benchmark.
    50% comes from concentration proximity to the two-category parity HHI.

    This is NOT an IFRS-defined score.
    """
    gap = gender_share_gap(female_share, parity_benchmark)
    gap_score = clamp(100.0 * (1.0 - gap / max(parity_benchmark, 1e-9)))

    parity_hhi = parity_benchmark**2 + (1.0 - parity_benchmark)**2
    concentration_penalty = abs(hhi_value - parity_hhi)
    concentration_score = clamp(
        100.0 * (1.0 - concentration_penalty / max(1.0 - parity_hhi, 1e-9))
    )

    return round(0.5 * gap_score + 0.5 * concentration_score, 2)


def assess_governance(
    male_count: int,
    female_count: int,
    parity_benchmark: float = DEFAULT_PARITY_BENCHMARK,
    two_thirds_threshold: float = 2 / 3,
) -> GovernanceResult:
    total = male_count + female_count
    if total <= 0:
        raise ValueError("Total gender observations must be greater than zero.")
    if male_count < 0 or female_count < 0:
        raise ValueError("Gender counts cannot be negative.")

    male_share = male_count / total
    female_share = female_count / total
    current_hhi = hhi([male_share, female_share])
    parity_hhi = parity_benchmark**2 + (1 - parity_benchmark)**2

    gap = gender_share_gap(female_share, parity_benchmark)
    integrity = governance_integrity_score(
        female_share, current_hhi, parity_benchmark
    )

    if integrity >= 80:
        risk = "LOW"
    elif integrity >= 60:
        risk = "MODERATE"
    elif integrity >= 40:
        risk = "HIGH"
    else:
        risk = "CRITICAL"

    return GovernanceResult(
        male_share=round(male_share, 4),
        female_share=round(female_share, 4),
        parity_benchmark=parity_benchmark,
        gender_share_gap=round(gap, 4),
        hhi=round(current_hhi, 4),
        parity_hhi=round(parity_hhi, 4),
        hhi_excess=round(current_hhi - parity_hhi, 4),
        two_thirds_threshold=two_thirds_threshold,
        female_meets_two_thirds=female_share >= two_thirds_threshold,
        governance_integrity_score=integrity,
        governance_risk=risk,
    )


# ---------------------------------------------------------------------------
# IFRS S2 Climate Engine
# ---------------------------------------------------------------------------

def greenhouse_gas_intensity(
    scope1_tco2e: float,
    scope2_tco2e: float,
    total_output: float,
) -> float:
    """Calculate Scope 1 + Scope 2 emissions intensity."""
    if scope1_tco2e < 0 or scope2_tco2e < 0:
        raise ValueError("Emissions cannot be negative.")
    if total_output <= 0:
        raise ValueError("Total output must be greater than zero.")

    return (scope1_tco2e + scope2_tco2e) / total_output


def assess_climate(
    scope1_tco2e: float,
    scope2_tco2e: float,
    total_output: float,
    unit: str = "tCO2e/output-unit",
) -> ClimateResult:
    intensity = greenhouse_gas_intensity(
        scope1_tco2e, scope2_tco2e, total_output
    )
    total = scope1_tco2e + scope2_tco2e

    return ClimateResult(
        scope1_tco2e=round(scope1_tco2e, 4),
        scope2_tco2e=round(scope2_tco2e, 4),
        total_scope1_scope2_tco2e=round(total, 4),
        total_output=round(total_output, 4),
        intensity=round(intensity, 6),
        unit=unit,
        arithmetic_valid=math.isfinite(intensity),
    )


# ---------------------------------------------------------------------------
# Data Quality Engine
# ---------------------------------------------------------------------------

DEFAULT_DQS_WEIGHTS = {
    "source_integrity": 0.20,
    "traceability": 0.20,
    "completeness": 0.20,
    "consistency": 0.20,
    "verification": 0.20,
}


def validate_weights(weights: Mapping[str, float]) -> None:
    if any(v < 0 for v in weights.values()):
        raise ValueError("Weights cannot be negative.")
    if not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-9):
        raise ValueError("DQS weights must sum to 1.0.")


def calculate_dqs(
    source_integrity: float,
    traceability: float,
    completeness: float,
    consistency: float,
    verification: float,
    weights: Optional[Mapping[str, float]] = None,
) -> DataQualityResult:
    weights = dict(weights or DEFAULT_DQS_WEIGHTS)
    validate_weights(weights)

    scores = {
        "source_integrity": source_integrity,
        "traceability": traceability,
        "completeness": completeness,
        "consistency": consistency,
        "verification": verification,
    }

    for name, score in scores.items():
        if not 0 <= score <= 100:
            raise ValueError(f"{name} must be between 0 and 100.")

    score = sum(scores[k] * weights[k] for k in scores)

    if score >= 90:
        tier = "ASSURANCE_READY"
    elif score >= 75:
        tier = "VERIFIED"
    elif score >= 60:
        tier = "CONTROLLED"
    elif score >= 40:
        tier = "DEVELOPING"
    else:
        tier = "MINIMAL"

    return DataQualityResult(
        source_integrity=round(source_integrity, 2),
        traceability=round(traceability, 2),
        completeness=round(completeness, 2),
        consistency=round(consistency, 2),
        verification=round(verification, 2),
        weights=weights,
        score=round(score, 2),
        tier=tier,
    )


# ---------------------------------------------------------------------------
# Verification Engine
# ---------------------------------------------------------------------------

def compare_values(
    reported_value: Optional[float],
    recalculated_value: Optional[float],
    tolerance_percentage: float = 1.0,
) -> Tuple[Optional[float], Optional[float], bool]:
    if reported_value is None or recalculated_value is None:
        return None, None, False

    variance = recalculated_value - reported_value

    if reported_value == 0:
        variance_percentage = 0.0 if recalculated_value == 0 else 100.0
    else:
        variance_percentage = abs(variance / reported_value) * 100.0

    match = variance_percentage <= tolerance_percentage
    return variance, variance_percentage, match


def verify_metric(
    metric: str,
    reported_value: Optional[float],
    recalculated_value: Optional[float],
    source_exists: bool,
    evidence_exists: bool,
    tolerance_percentage: float = 1.0,
) -> VerificationResult:
    variance, variance_percentage, arithmetic_match = compare_values(
        reported_value,
        recalculated_value,
        tolerance_percentage,
    )

    verification_id = f"VER-{uuid.uuid4().hex[:12].upper()}"

    if not source_exists:
        status = "EXCEPTION"
        code = "EX-SOURCE"
        message = "Source record could not be established."
    elif not evidence_exists:
        status = "EXCEPTION"
        code = "EX-EVIDENCE"
        message = "Supporting evidence could not be established."
    elif not arithmetic_match:
        status = "EXCEPTION"
        code = "EX-VARIANCE"
        message = "Reported and recalculated values exceed tolerance."
    else:
        status = "PASS"
        code = None
        message = None

    return VerificationResult(
        verification_id=verification_id,
        metric=metric,
        reported_value=reported_value,
        recalculated_value=recalculated_value,
        variance=round_or_none(variance),
        variance_percentage=round_or_none(variance_percentage),
        tolerance_percentage=tolerance_percentage,
        source_exists=source_exists,
        evidence_exists=evidence_exists,
        arithmetic_match=arithmetic_match,
        status=status,
        exception_code=code,
        exception_message=message,
        timestamp=utc_now(),
    )


def calculate_verification_score(
    results: Sequence[VerificationResult],
) -> float:
    if not results:
        return 0.0

    scores = []
    for result in results:
        score = 100.0
        if not result.source_exists:
            score -= 35
        if not result.evidence_exists:
            score -= 35
        if not result.arithmetic_match:
            score -= 30
        scores.append(clamp(score))

    return round(statistics.mean(scores), 2)


# ---------------------------------------------------------------------------
# Lineage Engine
# ---------------------------------------------------------------------------

class LineageGraph:
    def __init__(self) -> None:
        self.nodes: List[LineageNode] = []

    def add(
        self,
        node_id: str,
        node_type: str,
        description: str,
        parent_ids: Optional[List[str]] = None,
        payload: Optional[Any] = None,
    ) -> LineageNode:
        node = LineageNode(
            node_id=node_id,
            node_type=node_type,
            description=description,
            parent_ids=parent_ids or [],
            hash=sha256_hash(payload if payload is not None else description),
        )
        self.nodes.append(node)
        return node

    def to_list(self) -> List[LineageNode]:
        return list(self.nodes)


# ---------------------------------------------------------------------------
# Assurance Risk Engine
# ---------------------------------------------------------------------------

def classify_assurance_state(score: float) -> str:
    score = clamp(score)
    for threshold, state in RISK_THRESHOLDS:
        if score >= threshold:
            return state
    return "ZINC"


def risk_level_from_score(score: float) -> str:
    if score >= 80:
        return "LOW"
    if score >= 60:
        return "MODERATE"
    if score >= 40:
        return "HIGH"
    return "CRITICAL"


def calculate_forensic_assurance_index(
    governance_score: float,
    climate_data_quality_score: float,
    traceability_score: float,
    verification_score: float,
    exception_integrity_score: float,
    weights: Optional[Mapping[str, float]] = None,
) -> AssuranceResult:
    default_weights = {
        "governance": 0.20,
        "climate": 0.20,
        "traceability": 0.20,
        "verification": 0.25,
        "exception_integrity": 0.15,
    }

    weights = dict(weights or default_weights)
    validate_weights(weights)

    values = {
        "governance": governance_score,
        "climate": climate_data_quality_score,
        "traceability": traceability_score,
        "verification": verification_score,
        "exception_integrity": exception_integrity_score,
    }

    for key, value in values.items():
        if not 0 <= value <= 100:
            raise ValueError(f"{key} score must be between 0 and 100.")

    fai = sum(values[k] * weights[k] for k in values)
    state = classify_assurance_state(fai)
    risk_level = risk_level_from_score(fai)

    drivers = []
    if governance_score < 70:
        drivers.append("Governance integrity below 70%.")
    if climate_data_quality_score < 70:
        drivers.append("Climate data quality below 70%.")
    if traceability_score < 80:
        drivers.append("Evidence traceability requires improvement.")
    if verification_score < 80:
        drivers.append("Verification/control performance requires improvement.")
    if exception_integrity_score < 80:
        drivers.append("Exception rate or exception handling requires attention.")

    if not drivers:
        drivers.append("No major analytical risk driver identified.")

    return AssuranceResult(
        governance_score=round(governance_score, 2),
        climate_data_quality_score=round(climate_data_quality_score, 2),
        traceability_score=round(traceability_score, 2),
        verification_score=round(verification_score, 2),
        exception_integrity_score=round(exception_integrity_score, 2),
        forensic_assurance_index=round(fai, 2),
        assurance_state=state,
        risk_level=risk_level,
        drivers=drivers,
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def report_to_dict(report: DiagnosticReport) -> Dict[str, Any]:
    return asdict(report)


def write_json_report(report: DiagnosticReport, output_path: Path) -> None:
    ensure_directory(output_path.parent)
    output_path.write_text(
        json.dumps(report_to_dict(report), indent=2, default=str),
        encoding="utf-8",
    )


def write_csv_audit_log(
    results: Sequence[VerificationResult],
    output_path: Path,
) -> None:
    ensure_directory(output_path.parent)

    fieldnames = [
        "verification_id",
        "metric",
        "reported_value",
        "recalculated_value",
        "variance",
        "variance_percentage",
        "tolerance_percentage",
        "source_exists",
        "evidence_exists",
        "arithmetic_match",
        "status",
        "exception_code",
        "exception_message",
        "timestamp",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))


def print_report(report: DiagnosticReport) -> None:
    g = report.governance
    c = report.climate
    q = report.data_quality
    a = report.assurance

    print("=" * 70)
    print(" IFRS FORENSIC ASSURANCE ALGORITHM")
    print("=" * 70)
    print(f"Entity:            {report.entity}")
    print(f"Reporting Period:  {report.reporting_period}")
    print(f"Generated:         {report.generated_at}")

    print("\n" + "-" * 70)
    print("IFRS S1 — GOVERNANCE")
    print("-" * 70)
    print(f"Male Share:                 {g.male_share:.2%}")
    print(f"Female Share:               {g.female_share:.2%}")
    print(f"Gender Share Gap:           {g.gender_share_gap:.2%}")
    print(f"Adjusted/Observed HHI:      {g.hhi:.4f}")
    print(f"Parity HHI:                 {g.parity_hhi:.4f}")
    print(f"Two-Thirds Benchmark Met:   {g.female_meets_two_thirds}")
    print(f"Governance Integrity:       {g.governance_integrity_score:.2f}%")
    print(f"Governance Risk:             {g.governance_risk}")

    print("\n" + "-" * 70)
    print("IFRS S2 — CLIMATE")
    print("-" * 70)
    print(f"Scope 1:                    {c.scope1_tco2e:,.2f} tCO2e")
    print(f"Scope 2:                    {c.scope2_tco2e:,.2f} tCO2e")
    print(f"Total Scope 1 + 2:         {c.total_scope1_scope2_tco2e:,.2f} tCO2e")
    print(f"Total Output:               {c.total_output:,.2f}")
    print(f"Climate Intensity:          {c.intensity:.6f} {c.unit}")
    print(f"Arithmetic Valid:           {c.arithmetic_valid}")

    print("\n" + "-" * 70)
    print("DATA QUALITY SCORE")
    print("-" * 70)
    print(f"Source Integrity:           {q.source_integrity:.2f}%")
    print(f"Traceability:               {q.traceability:.2f}%")
    print(f"Completeness:               {q.completeness:.2f}%")
    print(f"Consistency:                {q.consistency:.2f}%")
    print(f"Verification:               {q.verification:.2f}%")
    print(f"DQS:                        {q.score:.2f}%")
    print(f"Data Quality Tier:          {q.tier}")

    print("\n" + "-" * 70)
    print("FORENSIC VERIFICATION")
    print("-" * 70)
    print(f"Metrics Tested:             {len(report.verification_results)}")
    print(f"Exceptions:                 {len(report.exceptions)}")

    for result in report.verification_results:
        print(
            f"  {result.metric}: {result.status}"
            + (
                f" ({result.variance_percentage:.2f}% variance)"
                if result.variance_percentage is not None
                else ""
            )
        )

    print("\n" + "-" * 70)
    print("FORENSIC ASSURANCE")
    print("-" * 70)
    print(f"Forensic Assurance Index:   {a.forensic_assurance_index:.2f}%")
    print(f"Assurance State:             {a.assurance_state}")
    print(f"Risk Level:                 {a.risk_level}")
    print("Primary Drivers:")
    for driver in a.drivers:
        print(f"  - {driver}")

    print("\n" + "=" * 70)
    print("Research prototype — not an audit or assurance opinion.")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Reference diagnostic pipeline
# ---------------------------------------------------------------------------

def build_reference_report() -> DiagnosticReport:
    entity = "Example Corporation"
    period = "FY2025"

    # -----------------------------
    # IFRS S1 reference inputs
    # -----------------------------
    governance = assess_governance(
        male_count=58,
        female_count=42,
        parity_benchmark=0.50,
        two_thirds_threshold=2 / 3,
    )

    # -----------------------------
    # IFRS S2 reference inputs
    # -----------------------------
    climate = assess_climate(
        scope1_tco2e=8450,
        scope2_tco2e=6320,
        total_output=35000,
        unit="tCO2e/output-unit",
    )

    # -----------------------------
    # Data Quality
    # -----------------------------
    dqs = calculate_dqs(
        source_integrity=91,
        traceability=88,
        completeness=83,
        consistency=94,
        verification=79,
    )

    # -----------------------------
    # Verification examples
    # -----------------------------
    # Example 1: climate metric passes.
    climate_reported_total = 14770
    climate_recalculated_total = (
        climate.scope1_tco2e + climate.scope2_tco2e
    )

    verification_1 = verify_metric(
        metric="Scope 1 + Scope 2 Emissions",
        reported_value=climate_reported_total,
        recalculated_value=climate_recalculated_total,
        source_exists=True,
        evidence_exists=True,
        tolerance_percentage=1.0,
    )

    # Example 2: a small but intentional exception.
    verification_2 = verify_metric(
        metric="Scope 2 Supplier Dataset",
        reported_value=6320,
        recalculated_value=6411,
        source_exists=True,
        evidence_exists=True,
        tolerance_percentage=1.0,
    )

    # Example 3: governance disclosure supported by records.
    verification_3 = verify_metric(
        metric="Female Board/Leadership Representation",
        reported_value=42,
        recalculated_value=42,
        source_exists=True,
        evidence_exists=True,
        tolerance_percentage=0.0,
    )

    verification_results = [
        verification_1,
        verification_2,
        verification_3,
    ]

    verification_score = calculate_verification_score(
        verification_results
    )

    # Traceability is independently derived from DQS and evidence coverage.
    traceability_score = dqs.traceability

    # Exception integrity:
    # 100 when all tests pass, declining according to exception rate.
    total_tests = len(verification_results)
    exception_count = sum(
        1 for r in verification_results if r.status == "EXCEPTION"
    )
    exception_rate = exception_count / total_tests if total_tests else 1.0
    exception_integrity_score = clamp(100 * (1 - exception_rate))

    assurance = calculate_forensic_assurance_index(
        governance_score=governance.governance_integrity_score,
        climate_data_quality_score=dqs.score,
        traceability_score=traceability_score,
        verification_score=verification_score,
        exception_integrity_score=exception_integrity_score,
    )

    # -----------------------------
    # Evidence lineage
    # -----------------------------
    graph = LineageGraph()

    graph.add(
        node_id="SRC-001",
        node_type="SOURCE",
        description="HR governance dataset",
        payload={"male": 58, "female": 42},
    )

    graph.add(
        node_id="CALC-001",
        node_type="CALCULATION",
        description="Gender share and HHI calculation",
        parent_ids=["SRC-001"],
        payload=asdict(governance),
    )

    graph.add(
        node_id="SRC-002",
        node_type="SOURCE",
        description="Scope 1 and Scope 2 emissions dataset",
        payload={
            "scope1": climate.scope1_tco2e,
            "scope2": climate.scope2_tco2e,
        },
    )

    graph.add(
        node_id="CALC-002",
        node_type="CALCULATION",
        description="GHG intensity calculation",
        parent_ids=["SRC-002"],
        payload=asdict(climate),
    )

    graph.add(
        node_id="DQS-001",
        node_type="QUALITY_SCORE",
        description="Weighted Data Quality Score",
        parent_ids=["SRC-002", "CALC-002"],
        payload=asdict(dqs),
    )

    graph.add(
        node_id="VER-001",
        node_type="VERIFICATION",
        description="Verification results",
        parent_ids=["CALC-001", "CALC-002", "DQS-001"],
        payload=[asdict(x) for x in verification_results],
    )

    graph.add(
        node_id="FAI-001",
        node_type="ASSURANCE_INDEX",
        description="Forensic Assurance Index",
        parent_ids=["DQS-001", "VER-001"],
        payload=asdict(assurance),
    )

    exceptions = [
        r for r in verification_results if r.status == "EXCEPTION"
    ]

    return DiagnosticReport(
        entity=entity,
        reporting_period=period,
        generated_at=utc_now(),
        governance=governance,
        climate=climate,
        data_quality=dqs,
        verification_results=verification_results,
        assurance=assurance,
        lineage=graph.to_list(),
        exceptions=exceptions,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    report = build_reference_report()

    print_report(report)

    base_dir = Path(__file__).resolve().parents[1]
    output_dir = base_dir / "data" / "processed"
    ensure_directory(output_dir)

    json_path = output_dir / "diagnostic_report.json"
    csv_path = output_dir / "verification_audit_log.csv"

    write_json_report(report, json_path)
    write_csv_audit_log(report.verification_results, csv_path)

    print("\nGenerated files:")
    print(f"  JSON report: {json_path}")
    print(f"  Audit log:   {csv_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
