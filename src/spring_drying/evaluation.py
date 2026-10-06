"""Model evaluation that respects spatial dependence between springs."""
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (accuracy_score, f1_score, precision_score, recall_score,
                             roc_auc_score)
from sklearn.model_selection import (LeaveOneGroupOut, StratifiedKFold, cross_val_predict,
                                     cross_validate)

from .config import RANDOM_STATE


def holdout_metrics(y_true, y_pred, y_proba) -> dict:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred),
        "recall": recall_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred),
        "roc_auc": roc_auc_score(y_true, y_proba),
    }


def cv_summary(model, X, y, groups) -> dict:
    """Shuffled stratified 5-fold CV (mean and sd over folds) plus a pooled
    leave-one-grid-cell-out ROC-AUC (whole areas held out)."""
    folds = StratifiedKFold(5, shuffle=True, random_state=RANDOM_STATE)
    cv = cross_validate(clone(model), X, y, cv=folds, scoring=["f1", "roc_auc"])
    area_proba = cross_val_predict(clone(model), X, y, cv=LeaveOneGroupOut(), groups=groups,
                                   method="predict_proba")[:, 1]
    return {
        "cv_f1_mean": cv["test_f1"].mean(), "cv_f1_sd": cv["test_f1"].std(),
        "cv_auc_mean": cv["test_roc_auc"].mean(), "cv_auc_sd": cv["test_roc_auc"].std(),
        "new_area_auc": roc_auc_score(y, area_proba),
    }


def compare_random_vs_spatial_cv(model, X, y, groups) -> pd.DataFrame:
    """Out-of-fold ROC-AUC/F1 under (a) shuffled stratified 5-fold and
    (b) leave-one-grid-cell-out. A large gap means the model is memorising
    location rather than learning a transferable relationship."""
    schemes = {
        "random 5-fold": (StratifiedKFold(5, shuffle=True, random_state=RANDOM_STATE), None),
        "leave-one-cell-out": (LeaveOneGroupOut(), groups),
    }
    rows = []
    for name, (cv, g) in schemes.items():
        proba = cross_val_predict(clone(model), X, y, cv=cv, groups=g, method="predict_proba")[:, 1]
        rows.append({"cv": name, "roc_auc": roc_auc_score(y, proba), "f1@0.5": f1_score(y, proba > 0.5)})
    return pd.DataFrame(rows)
