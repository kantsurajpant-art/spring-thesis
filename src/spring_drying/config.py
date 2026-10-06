"""Central paths and constants shared by every notebook and script.

Large inputs (the ERA5-Land NetCDF and Full_Analysis_data.csv) are NOT kept in
the repository. The data directory is resolved in this order:

1. the ``SPRING_DATA_DIR`` environment variable, if set;
2. ``<repo>/data`` if it contains ``Full_Analysis_data.csv``;
3. the sibling ``../Project Preperation Rough`` folder (current OneDrive layout).
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

NC_FILENAME = "baf400466b67369cecb11d5d456ba48c.nc"
ANALYSIS_CSV_FILENAME = "Full_Analysis_data.csv"


def _resolve_data_dir() -> Path:
    candidates = []
    if os.environ.get("SPRING_DATA_DIR"):
        candidates.append(Path(os.environ["SPRING_DATA_DIR"]))
    candidates += [REPO_ROOT / "data", REPO_ROOT.parent / "Project Preperation Rough"]
    for c in candidates:
        if (c / ANALYSIS_CSV_FILENAME).exists():
            return c.resolve()
    raise FileNotFoundError(
        f"{ANALYSIS_CSV_FILENAME} not found in any of: "
        + ", ".join(str(c) for c in candidates)
        + ". Set SPRING_DATA_DIR or copy the data into <repo>/data (see data/README.md)."
    )


DATA_DIR = _resolve_data_dir()
NC_PATH = DATA_DIR / NC_FILENAME
ANALYSIS_CSV_PATH = DATA_DIR / ANALYSIS_CSV_FILENAME

# Raw 7-municipality ICIMOD survey export (source of "Reason of drying").
RAW_SURVEY_FILENAME = "Overall assessment_SS mapping-7 municipalities.csv"
RAW_SURVEY_PATH = next(
    (p for p in [DATA_DIR / RAW_SURVEY_FILENAME,
                 REPO_ROOT.parent / "9-credit Project" / "document for vscode format" / RAW_SURVEY_FILENAME]
     if p.exists()),
    DATA_DIR / RAW_SURVEY_FILENAME,
)

RESULTS_DIR = REPO_ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42

# Climate window: 15 years ending at the survey year, inclusive (2009-2023).
# The spring inventory was surveyed Sep 2023 - early 2024 and the latest reported
# drying year is 2023, so active/dried status describes conditions up to 2023.
# (The original notebooks used 2025, which includes years after the survey.)
SURVEY_YEAR = 2023
WINDOW_END = SURVEY_YEAR
WINDOW_LEN = 15

# ERA5-Land monthly means start in 1950, so a full 15-year window must end >= 1964.
ERA5_LAND_FIRST_YEAR = 1950
