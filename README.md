# IFRS Forensic Assurance Algorithm

A system-agnostic, transaction-level verification engine for **IFRS S1 (Governance)** and **IFRS S2 (Climate)** disclosures.

## Key Features
- **IFRS S1 Engine**: Measures board diversity gaps ($\Delta G$) and concentration risk using an adjusted Herfindahl-Hirschman Index (HHI).
- **IFRS S2 Engine**: Evaluates climate disclosures using a multi-weighted 5-Tier Data Quality Score (DQS).
- **Risk Classifier**: Maps system metrics to continuous audit risk tiers (Alpha to Zinc).

## Execution
Run the reference implementation using Python standard library:
```bash
python src/forensic_algorithm.py
