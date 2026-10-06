"""Quick stand-alone check: random vs leave-one-grid-cell-out CV for the fixed-window features.

The full, reported version of this analysis is notebooks/05_model3_final.ipynb (VIF inside the
pipeline, 2,000 trees); this script is a fast sanity check with a plain 500-tree forest.

Usage (from the repo root):  python scripts/spatial_cv_check.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from spring_drying.climate import fixed_window_features, grid_cell_ids
from spring_drying.config import RANDOM_STATE, TABLES_DIR, WINDOW_END, WINDOW_LEN
from spring_drying.data import load_springs
from spring_drying.evaluation import compare_random_vs_spatial_cv

springs = load_springs()
features_csv = TABLES_DIR / "climate_features_version_b.csv"  # written by notebooks/01_climate_features
if features_csv.exists():
    climate = pd.read_csv(features_csv)
else:
    climate = fixed_window_features(springs["Latitude"].values, springs["Longitude"].values)
    climate.to_csv(features_csv, index=False)
print(f"Climate window: {WINDOW_END - WINDOW_LEN + 1}-{WINDOW_END}  ({features_csv.name})")
groups = grid_cell_ids(springs["Latitude"].values, springs["Longitude"].values)
y = springs["dried"].values
print(f"{len(springs)} springs fall in {len(set(groups))} distinct climate grid cells\n")

climate_cols = ["Dewpoint_rate", "Temperature_rate", "Precipitation_rate",
                "Temperature_mean", "Precipitation_mean", "Evaporation_mean"]
feature_sets = {
    "climate only": climate[climate_cols],
    "perennial only": springs[["perennial"]],
    "climate + perennial": climate[climate_cols].assign(perennial=springs["perennial"].values),
}
rf = RandomForestClassifier(n_estimators=500, class_weight="balanced",
                            random_state=RANDOM_STATE, n_jobs=-1)
for name, X in feature_sets.items():
    res = compare_random_vs_spatial_cv(rf, X.values.astype(float), y, groups)
    print(name); print(res.to_string(index=False, float_format="%.3f")); print()
