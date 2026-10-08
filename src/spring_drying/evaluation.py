"""Model evaluation that respects spatial dependence between springs."""
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (accuracy_score, average_precision_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import (LeaveOneGroupOut, StratifiedKFold, cross_val_predict,
                                     cross_validate)

from .config import RANDOM_STATE


def holdout_metrics(y_true, y_pred, y_proba) -> dict:
    """pr_auc is the average precision (area under the precision-recall curve); a random
    ranking scores the share of dried springs, so read it against that baseline."""
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred),
        "recall": recall_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred),
        "roc_auc": roc_auc_score(y_true, y_proba),
        "pr_auc": average_precision_score(y_true, y_proba),
    }


def bootstrap_ci(y_true, y_proba, n_boot=2000, level=0.95) -> dict:
    """Percentile bootstrap CI of test ROC-AUC and PR-AUC: resample the test springs with
    replacement (the fitted model is fixed), so it reflects test-set sampling variability only."""
    y_true, y_proba = np.asarray(y_true), np.asarray(y_proba)
    rng = np.random.default_rng(RANDOM_STATE)
    auc, ap = [], []
    while len(auc) < n_boot:
        i = rng.integers(0, len(y_true), len(y_true))
        if y_true[i].min() == y_true[i].max():  # a resample with one class has no AUC
            continue
        auc.append(roc_auc_score(y_true[i], y_proba[i]))
        ap.append(average_precision_score(y_true[i], y_proba[i]))
    q = [100 * (1 - level) / 2, 100 * (1 + level) / 2]
    return {"n_boot": n_boot, "level": level,
            "roc_auc": [float(v) for v in np.percentile(auc, q)],
            "pr_auc": [float(v) for v in np.percentile(ap, q)]}


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
