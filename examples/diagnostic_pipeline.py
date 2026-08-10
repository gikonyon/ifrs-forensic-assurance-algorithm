from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.forensic_algorithm import build_reference_report, print_report

if __name__ == "__main__":
    report = build_reference_report()
    print_report(report)
