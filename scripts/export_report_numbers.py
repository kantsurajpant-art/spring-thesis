"""Collect every number the report quotes into report/numbers.json.

The report source (report/src/report.md) never contains hand-typed statistics: each
one is a {{placeholder}} resolved from this file, which is assembled only from the
JSON outputs the notebooks write to results/tables/.

Usage (from the repo root, after running notebooks 00-05):  python scripts/export_report_numbers.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"

SOURCES = {
    "facts": "dataset_facts.json",
    "climate": "climate_facts.json",
    "checks": "model3_checks.json",
    "m1": "model1_exploratory_metrics.json",
    "m2": "model2_refined_metrics.json",
    "m3va": "model3_version_a_metrics.json",
    "m3": "model3_final_metrics.json",
    "m3b": "model3b_drought_metrics.json",
    "m3bc": "model3b_drought_climate_only_metrics.json",
    "type": "cmp_type_only_metrics.json",
    "clim": "cmp_climate_only_metrics.json",
    "eq": "cmp_earthquake_metrics.json",
}


def main():
    numbers = {}
    for key, fname in SOURCES.items():
        path = TABLES / fname
        if not path.exists():
            raise FileNotFoundError(f"{path} missing - run the notebooks first")
        numbers[key] = json.loads(path.read_text(encoding="utf-8-sig"))
    out = ROOT / "report" / "numbers.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(numbers, indent=2), encoding="utf-8")
    print("wrote", out, "with", len(numbers), "sources")


if __name__ == "__main__":
    main()
