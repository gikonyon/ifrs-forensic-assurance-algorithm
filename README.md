# IFRS Forensic Assurance Algorithm

A system-agnostic, transaction-level verification engine for analytical
assessment of selected **IFRS S1** and **IFRS S2** sustainability disclosures.

## Overview

The IFRS Forensic Assurance Algorithm is a Python research prototype designed
to move sustainability assurance from predominantly narrative review toward
continuous, evidence-based and transaction-level verification.

The reference implementation combines:

- IFRS S1-oriented governance analytics
- IFRS S2-oriented climate calculations
- Gender Share Gap
- Herfindahl-Hirschman concentration analysis
- Greenhouse Gas intensity
- Five-tier Data Quality Score
- Evidence and data lineage
- Mathematical recalculation
- Exception detection
- Explainable Assurance Risk Classification
- Machine-readable JSON reports
- CSV verification audit logs
- Automated unit tests

> **Important:** This is a research prototype. It is not an audit opinion,
> assurance opinion, legal interpretation of IFRS S1/S2, or substitute for
> professional judgement.

## Architecture

```text
SOURCE EVIDENCE
      |
      v
DATA EXTRACTION / NORMALISATION
      |
      v
DATA LINEAGE
      |
      +--------------------+
      |                    |
      v                    v
IFRS S1 ENGINE        IFRS S2 ENGINE
Governance            Climate
      |                    |
      +---------+----------+
                |
                v
        VERIFICATION ENGINE
                |
                v
         DATA QUALITY SCORE
                |
                v
        EXCEPTION DETECTION
                |
                v
       FORENSIC ASSURANCE INDEX
                |
                v
      ASSURANCE RISK STATE
                |
                v
       AUDIT / EVIDENCE LOG
```

## Quick Start

Requirements:

- Python 3.9+
- No external dependencies

Run:

```bash
python src/forensic_algorithm.py
```

Run tests:

```bash
python -m unittest discover tests -v
```

Or:

```bash
python examples/diagnostic_pipeline.py
```

## Outputs

Running the main pipeline creates:

```text
data/
└── processed/
    ├── diagnostic_report.json
    └── verification_audit_log.csv
```

## Core Mathematical Models

### Gender Share Gap

```text
Delta G = |Observed Gender Share - Benchmark|
```

### HHI

```text
HHI = sum(share_i ^ 2)
```

Shares are represented as decimals between 0 and 1.

### GHG Intensity

```text
Ic = (Scope 1 + Scope 2) / Total Output
```

### Data Quality Score

```text
DQS = sum(weight_i * score_i)
```

### Forensic Assurance Index

```text
FAI =
  Governance Score
+ Climate Data Quality
+ Traceability
+ Verification
+ Exception Integrity

subject to configured weights.
```

## Governance Engine

The governance engine evaluates:

- male and female representation;
- Gender Share Gap;
- observed HHI;
- parity HHI;
- a two-thirds analytical benchmark; and
- a research-specific Governance Integrity Score.

The two-thirds benchmark is a jurisdiction-specific analytical reference
where applicable. It is not an IFRS requirement.

## Climate Engine

The climate engine calculates:

- Scope 1 emissions;
- Scope 2 emissions;
- combined Scope 1 + Scope 2 emissions;
- total output; and
- emissions intensity.

The denominator must be appropriate for the reporting context.

## Data Quality Engine

Five dimensions are scored:

| Dimension | Meaning |
|---|---|
| Source Integrity | Reliability of originating evidence |
| Traceability | Ability to follow data to its source |
| Completeness | Availability of required information |
| Consistency | Agreement across datasets and periods |
| Verification | Evidence of control or verification |

The prototype classifies DQS into:

1. MINIMAL
2. DEVELOPING
3. CONTROLLED
4. VERIFIED
5. ASSURANCE_READY

These are research classifications, not IFRS assurance levels.

## Verification Engine

Each verification test can compare:

```text
Reported Value
      vs.
Recalculated Value
```

and test:

- source existence;
- evidence existence;
- arithmetic agreement;
- tolerance;
- exception status.

Example exception:

```text
Metric: Scope 2 Supplier Dataset
Reported: 6320
Recalculated: 6411
Variance: 1.44%
Status: EXCEPTION
```

## Lineage

The prototype creates a simple lineage graph:

```text
SOURCE
  |
  v
CALCULATION
  |
  v
QUALITY SCORE
  |
  v
VERIFICATION
  |
  v
ASSURANCE INDEX
```

Each lineage node can carry a SHA-256 hash of its payload to support evidence
integrity and reproducibility.

## Assurance States

The research prototype uses:

```text
ALPHA -> BETA -> GAMMA -> ... -> OMEGA -> ZINC
```

The state is derived from the Forensic Assurance Index.

These names are not IFRS-defined assurance opinions.

## Research Position

The research proposition is:

> Sustainability information should, where practicable, be capable of being
> traced from a reported disclosure to its underlying evidence, reproduced
> through an identifiable calculation, subjected to control tests, and
> assigned an explainable verification-risk state.

The intended transition is:

```text
Narrative Disclosure
        |
        v
Evidence
        |
        v
Recalculation
        |
        v
Control Testing
        |
        v
Exception Detection
        |
        v
Continuous Assurance
```

## Limitations

The system does not:

- issue an audit opinion;
- determine legal compliance;
- replace auditors;
- determine materiality automatically;
- prove fraud from anomalies;
- replace management judgement;
- replace IFRS interpretation; or
- guarantee the reliability of source data.

An exception means that further investigation may be appropriate. It does not,
by itself, establish fraud or misstatement.

## Author

**Gikonyo Ndugu**

Independent Researcher / Consultant

Nairobi, Kenya

## Citation

Ndugu, G. (2026). *IFRS Forensic Assurance Algorithm: A Transaction-Level
Verification Engine for IFRS S1 and IFRS S2 Sustainability Disclosures.*
Research Prototype, Nairobi, Kenya.
