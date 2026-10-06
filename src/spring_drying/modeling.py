"""Model 3 pipeline: VIF screening fitted on training data only, then Random Forest.

Putting VIF inside the Pipeline means every train/test split and every
cross-validation fold chooses its features from its own training rows only.
"""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import RANDOM_STATE

CLIMATE_COLS = ["Dewpoint_rate", "Temperature_rate", "Precipitation_rate", "Evaporation_rate",
                "Dewpoint_mean", "Temperature_mean", "Precipitation_mean", "Evaporation_mean"]


def compute_vif(frame: pd.DataFrame, cols) -> pd.Series:
    """VIF_i = 1 / (1 - R_i^2), regressing each standardised column on the others."""
    z = (frame[cols] - frame[cols].mean()) / frame[cols].std(ddof=0)
    vifs = {}
    for c in cols:
        others = z.drop(columns=[c]).values
        r2 = LinearRegression().fit(others, z[c].values).score(others, z[c].values)
        vifs[c] = np.inf if r2 >= 0.999999 else 1.0 / (1.0 - r2)
    return pd.Series(vifs).sort_values(ascending=False)


class VIFSelector(BaseEstimator, TransformerMixin):
    """Iteratively drop the `screen_cols` column with the highest VIF until all are
    <= threshold (or `min_keep` remain). Other columns pass through untouched."""

    def __init__(self, screen_cols=tuple(CLIMATE_COLS), threshold=10.0, min_keep=2):
        self.screen_cols = screen_cols
        self.threshold = threshold
        self.min_keep = min_keep

    def fit(self, X, y=None):
        cols = [c for c in self.screen_cols if c in X.columns]
        self.dropped_ = []
        while len(cols) > self.min_keep:
            vif = compute_vif(X, cols)
            if vif.iloc[0] <= self.threshold:
                break
            self.dropped_.append((vif.index[0], round(float(vif.iloc[0]), 2)))
            cols.remove(vif.index[0])
        self.final_vif_ = compute_vif(X, cols) if len(cols) > 1 else pd.Series(dtype=float)
        self.selected_ = cols + [c for c in X.columns if c not in self.screen_cols]
        return self

    def transform(self, X):
        return X[self.selected_]

    def get_feature_names_out(self, input_features=None):
        return np.array(self.selected_)


def make_rf(n_estimators=2000) -> Pipeline:
    """Random Forest without VIF screening (Models 1 and 2, the exploratory models)."""
    return Pipeline([
        ("scaler", StandardScaler()),
        ("rf", RandomForestClassifier(n_estimators=n_estimators, class_weight="balanced",
                                      random_state=RANDOM_STATE, n_jobs=-1)),
    ])


def make_model3(n_estimators=2000) -> Pipeline:
    """Same Random Forest settings as the report (2000 trees, balanced class weights).
    StandardScaler has no effect on a Random Forest; kept only for continuity with the report."""
    return Pipeline([
        ("vif", VIFSelector()),
        ("scaler", StandardScaler()),
        ("rf", RandomForestClassifier(n_estimators=n_estimators, class_weight="balanced",
                                      random_state=RANDOM_STATE, n_jobs=-1)),
    ])
