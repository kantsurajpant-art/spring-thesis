"""One function that trains, evaluates, plots and records a model configuration.

Every model in the report (Models 1, 2, 3 Version A, 3, 3b and the comparisons) goes
through `run_experiment`, so all of them share the same split, cross-validation,
metrics, importance measures and figure style, and every number is saved to JSON.
"""
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.base import clone
from sklearn.inspection import permutation_importance
from sklearn.metrics import RocCurveDisplay, confusion_matrix, roc_auc_score
from sklearn.model_selection import (LeaveOneGroupOut, StratifiedKFold, cross_val_predict,
                                     cross_validate, train_test_split)

from .config import FIGURES_DIR, RANDOM_STATE, TABLES_DIR
from .evaluation import holdout_metrics
from .modeling import compute_vif


def _feature_names(fitted, X):
    if "vif" in fitted.named_steps:
        return list(fitted.named_steps["vif"].selected_)
    return list(X.columns)


def run_experiment(name, title, X, y, model, groups=None, new_area=False,
                   make_figures=True, n_repeats=10, top_n=15):
    """Fit on a stratified 70/30 split, then report test metrics, shuffled 5-fold CV,
    optional leave-one-grid-cell-out AUC, impurity and permutation importance.

    Saves results/tables/<name>_metrics.json and, if make_figures,
    results/figures/<name>_confusion_roc.png and <name>_feature_importance.png."""
    X = X.astype(float)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, stratify=y, random_state=RANDOM_STATE)
    fitted = clone(model).fit(X_tr, y_tr)
    y_pred = fitted.predict(X_te)
    y_proba = fitted.predict_proba(X_te)[:, 1]
    cm = confusion_matrix(y_te, y_pred)
    tn, fp, fn, tp = (int(v) for v in cm.ravel())

    folds = StratifiedKFold(5, shuffle=True, random_state=RANDOM_STATE)
    cv = cross_validate(clone(model), X, y, cv=folds, scoring=["f1", "roc_auc"])

    names = _feature_names(fitted, X)
    impurity = pd.Series(fitted[-1].feature_importances_, index=names).sort_values(ascending=False)
    perm = permutation_importance(fitted, X_te, y_te, scoring="roc_auc", n_repeats=n_repeats,
                                  random_state=RANDOM_STATE)
    permutation = pd.Series(perm.importances_mean, index=X_te.columns)[names].sort_values(ascending=False)

    result = {
        "name": name, "title": title,
        "n_rows": int(len(X)), "n_dried": int(np.sum(y)), "n_features_in": int(X.shape[1]),
        "features_in": list(X.columns), "features_used": names,
        "n_train": int(len(X_tr)), "n_test": int(len(X_te)), "n_test_dried": int(np.sum(y_te)),
        "test": {k: float(v) for k, v in holdout_metrics(y_te, y_pred, y_proba).items()},
        "confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "cv": {"f1_mean": float(cv["test_f1"].mean()), "f1_sd": float(cv["test_f1"].std()),
               "auc_mean": float(cv["test_roc_auc"].mean()), "auc_sd": float(cv["test_roc_auc"].std()),
               "f1_folds": [float(v) for v in cv["test_f1"]]},
        "importance_impurity": {k: float(v) for k, v in impurity.items()},
        "importance_permutation": {k: float(v) for k, v in permutation.items()},
        "n_distinct_feature_rows": int(X.round(9).drop_duplicates().shape[0]),
    }
    if "vif" in fitted.named_steps:
        vif = fitted.named_steps["vif"]
        screen = [c for c in vif.screen_cols if c in X_tr.columns]
        result["vif"] = {
            "initial": {k: float(v) for k, v in compute_vif(X_tr, screen).items()} if len(screen) > 1 else {},
            "dropped": [[c, float(v)] for c, v in vif.dropped_],
            "final": {k: float(v) for k, v in vif.final_vif_.items()},
        }
    if new_area and groups is not None:
        proba = cross_val_predict(clone(model), X, y, cv=LeaveOneGroupOut(), groups=groups,
                                  method="predict_proba")[:, 1]
        result["new_area_auc"] = float(roc_auc_score(y, proba))
        result["n_groups"] = int(len(np.unique(groups)))

    if make_figures:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False, ax=axes[0],
                    xticklabels=["active (0)", "dried (1)"], yticklabels=["active (0)", "dried (1)"])
        axes[0].set_xlabel("Predicted"); axes[0].set_ylabel("True")
        axes[0].set_title(f"Confusion matrix: {title}")
        RocCurveDisplay.from_predictions(y_te, y_proba, ax=axes[1], name=title)
        axes[1].plot([0, 1], [0, 1], "k--", lw=1, label="Chance (AUC = 0.5)")
        axes[1].legend(loc="lower right", fontsize=9)
        axes[1].set_title(f"ROC curve: {title}")
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / f"{name}_confusion_roc.png", dpi=300)
        plt.show()

        top = impurity.head(top_n)
        fig, axes = plt.subplots(1, 2, figsize=(12, max(3.5, 0.35 * len(top) + 1.5)))
        sns.barplot(x=top.values, y=top.index, hue=top.index, palette="viridis", legend=False, ax=axes[0])
        axes[0].set_title("Impurity importance (share)"); axes[0].set_xlabel("Importance"); axes[0].set_ylabel("")
        ptop = permutation[top.index]
        sns.barplot(x=ptop.values, y=ptop.index, hue=ptop.index, palette="viridis", legend=False, ax=axes[1])
        axes[1].set_title("Permutation importance (drop in test ROC-AUC)")
        axes[1].set_xlabel("ROC-AUC drop"); axes[1].set_ylabel("")
        fig.suptitle(title)
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / f"{name}_feature_importance.png", dpi=300)
        plt.show()

    with open(TABLES_DIR / f"{name}_metrics.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result, fitted


def print_result(result):
    t, c, cv = result["test"], result["confusion"], result["cv"]
    print(f"{result['title']}  (n = {result['n_rows']}, dried = {result['n_dried']}, test = {result['n_test']})")
    print("  test: " + ", ".join(f"{k} {v:.3f}" for k, v in t.items()))
    print(f"  confusion: TN {c['tn']}  FP {c['fp']}  FN {c['fn']}  TP {c['tp']}")
    print(f"  5-fold CV (shuffled): F1 {cv['f1_mean']:.3f} +/- {cv['f1_sd']:.3f}, AUC {cv['auc_mean']:.3f} +/- {cv['auc_sd']:.3f}")
    if "new_area_auc" in result:
        print(f"  new-area (leave-one-grid-cell-out) AUC {result['new_area_auc']:.3f}")
    if "vif" in result:
        print(f"  VIF dropped: {result['vif']['dropped']}")
