"""Loading and encoding the spring inventory table."""
import pandas as pd

from .config import ANALYSIS_CSV_PATH, RAW_SURVEY_PATH

# The source column is named "Dried since how many years?" but actually stores the
# calendar YEAR the spring dried (e.g. 2017), not a duration.
DRIED_YEAR_COL = "Dried since how many years?"

# Survey answers to "Reason of drying" grouped into a few causes.
REASON_GROUPS = {
    "earthquake": "earthquake",
    "drought": "drought", "reduced precipitation": "drought",
    "infrastructure development": "infrastructure", "infrastructure_development": "infrastructure",
    "natural_disaster": "natural_disaster",
    "source_neglected": "neglect_or_disruption", "source_disruption": "neglect_or_disruption",
    "deforestation": "land_use", "pine plantation": "land_use",
}


def load_springs(path=ANALYSIS_CSV_PATH) -> pd.DataFrame:
    """Load the spring table, dropping any stray pandas index columns by name
    (never positionally with .iloc[:, 1:], which silently drops Latitude when
    the file was saved with index=False)."""
    df = pd.read_csv(path)
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])
    df["dried"] = (df["Source Condition"].str.strip().str.lower() == "dried").astype(int)
    df["perennial"] = (df["Perennial / Seasonal"].str.strip().str.lower() == "perennial").astype(int)
    df["dried_year"] = df[DRIED_YEAR_COL]
    return df


def _coord_key(df: pd.DataFrame) -> pd.Series:
    return df["Latitude"].round(5).astype(str) + "," + df["Longitude"].round(5).astype(str)


def attach_drying_reason(springs: pd.DataFrame, raw_path=RAW_SURVEY_PATH) -> pd.DataFrame:
    """Add `drying_reason` (grouped, see REASON_GROUPS) to dried springs by matching
    coordinates against dried records of the raw survey. Active springs get "active"."""
    raw = pd.read_csv(raw_path, low_memory=False, encoding="latin-1",
                      usecols=["Latitude", "Longitude", "Source Condition", "Reason of drying"])
    raw = raw.dropna(subset=["Latitude", "Longitude"])
    raw = raw[raw["Source Condition"].astype(str).str.strip().str.lower() == "dried"]
    raw = raw.assign(key=_coord_key(raw)).drop_duplicates("key")
    reason = (raw.set_index("key")["Reason of drying"].astype(str).str.strip().str.lower()
              .map(REASON_GROUPS).fillna("unknown"))
    out = springs.copy()
    out["drying_reason"] = _coord_key(out).map(reason).fillna("unknown")
    out.loc[out["dried"] == 0, "drying_reason"] = "active"
    return out
