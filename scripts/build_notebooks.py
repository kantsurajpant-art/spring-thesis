"""Generate the numbered analysis notebooks in notebooks/.

Usage (from the repo root):
    python scripts/build_notebooks.py
    cd notebooks; foreach ($nb in Get-ChildItem 0*.ipynb) { python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=3600 $nb }

Each notebook is thin: the logic lives in src/spring_drying/, and every number a
notebook produces is written to results/tables/*.json for the report builder.
"""
from pathlib import Path

import nbformat as nbf

NB_DIR = Path(__file__).resolve().parents[1] / "notebooks"

BOOT = r"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path.cwd().parent / "src"))  # run from notebooks/

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from spring_drying.config import (FIGURES_DIR, TABLES_DIR, RANDOM_STATE, WINDOW_END, WINDOW_LEN,
                                  SURVEY_YEAR, ERA5_LAND_FIRST_YEAR, RAW_SURVEY_PATH, NC_PATH)
from spring_drying.data import load_springs, attach_drying_reason

sns.set_style("whitegrid")
pd.set_option("display.width", 140)

def save_json(obj, name):
    def conv(o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, (np.ndarray,)): return o.tolist()
        raise TypeError(type(o))
    with open(TABLES_DIR / name, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=conv)
    print("saved", TABLES_DIR / name)
"""


def notebook(cells):
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.cells = [nbf.v4.new_markdown_cell(c[3:].strip()) if c.startswith("MD:") else nbf.v4.new_code_cell(c.strip())
                for c in cells]
    return nb


# ---------------------------------------------------------------- 00 dataset overview
NB00 = [
"""MD:
# 00 - Dataset overview and data-quality checks

Facts about the spring inventory that the report quotes: class balance, drying years,
survey dates, the reported cause of drying, data-quality checks, the descriptive terrain
and road figures, the external (non-Roshi) springs, and the size of the proposed temporal
augmentation. All numbers are saved to `results/tables/dataset_facts.json`.
""",
BOOT,
"""
from spring_drying.data import _coord_key
from spring_drying.climate import grid_cell_ids

springs = attach_drying_reason(load_springs())
facts = {}
n, nd = len(springs), int(springs["dried"].sum())
facts["n_springs"], facts["n_dried"], facts["n_active"] = n, nd, n - nd
facts["pct_dried"] = 100 * nd / n
facts["n_perennial"] = int(springs["perennial"].sum())
facts["n_seasonal"] = n - facts["n_perennial"]
facts["pct_perennial"] = 100 * facts["n_perennial"] / n
facts["pct_dried_perennial"] = 100 * springs.loc[springs["perennial"] == 1, "dried"].mean()
facts["pct_dried_seasonal"] = 100 * springs.loc[springs["perennial"] == 0, "dried"].mean()
print(pd.crosstab(springs["Perennial / Seasonal"], springs["Source Condition"], margins=True))
facts
""",
"""MD:
## Drying year (calendar year, AD)

The analysis table stores the year a spring dried in a column misleadingly named
*"Dried since how many years?"*. A complete 15-year ERA5-Land window needs an end year of
at least 1950 + 14 = 1964.
""",
"""
dy = springs.loc[springs["dried"] == 1, "dried_year"]
first_full_end = ERA5_LAND_FIRST_YEAR + WINDOW_LEN - 1
facts["drying_year"] = {
    "n_with_year": int(dy.notna().sum()), "n_missing": int(dy.isna().sum()),
    "min": int(dy.min()), "max": int(dy.max()), "median": float(dy.median()),
    "n_2015": int((dy == 2015).sum()), "pct_2015": 100 * float((dy == 2015).sum()) / nd,
    "first_complete_window_end": first_full_end,
    "n_before_first_complete": int((dy < first_full_end).sum()),
    "n_since_2000": int((dy >= 2000).sum()),
}
facts["drying_year"]
""",
"""MD:
## Raw survey: size, survey dates and the Bikram Sambat calendar
""",
"""
raw = pd.read_csv(RAW_SURVEY_PATH, low_memory=False, encoding="latin-1").dropna(how="all")
stype = raw["Source Type"].astype(str).str.strip().str.lower()
facts["raw"] = {"n_records": len(raw), "n_springs": int((stype == "spring").sum()),
                "n_ponds": int((stype == "pond").sum()),
                "springs_by_municipality": raw.loc[stype == "spring", "Municipality"].value_counts().to_dict()}

dates = pd.to_datetime(raw["Date"].astype(str).str.strip(), format="%d/%m/%Y", errors="coerce")
ok = dates[dates.dt.year.isin([2023, 2024])]
facts["survey_dates"] = {
    "n_records_with_date": int(raw["Date"].notna().sum()), "n_parsed_2023_2024": int(len(ok)),
    "pct_2024": 100 * float((ok.dt.year == 2024).mean()),
    "p05": str(ok.quantile(0.05).date()), "median": str(ok.quantile(0.5).date()), "p95": str(ok.quantile(0.95).date()),
}
print(ok.dt.to_period("M").value_counts().sort_index())

# Bikram Sambat (BS) drying years in the raw survey vs AD years in the analysis table
r = raw.dropna(subset=["Latitude", "Longitude"])
r = r[r["Source Condition"].astype(str).str.strip().str.lower() == "dried"]
r = r.assign(k=_coord_key(r)).drop_duplicates("k")
dried = springs[springs["dried"] == 1]
bs = pd.to_numeric(_coord_key(dried).map(r.set_index("k")["Dried since how many years?"]), errors="coerce")
offset = (bs.values - dried["dried_year"].values)
offset = pd.Series(offset[~np.isnan(offset)]).astype(int).value_counts()
facts["bs_to_ad_offset"] = {str(k): int(v) for k, v in offset.items()}
facts["survey_dates"], facts["bs_to_ad_offset"]
""",
"""MD:
## Reported cause of drying

Matched from the raw survey's *Reason of drying* field by coordinates
(*Drought* and *Reduced Precipitation* are grouped as **drought**).
""",
"""
cause = springs.loc[springs["dried"] == 1, "drying_reason"].value_counts()
facts["drying_cause"] = cause.to_dict()
eq = springs[(springs["dried"] == 1) & (springs["drying_reason"] == "earthquake")]
facts["earthquake_dried_in_2015"] = int((eq["dried_year"] == 2015).sum())
facts["n_dried_2015_by_cause"] = springs[(springs["dried"] == 1) & (springs["dried_year"] == 2015)]["drying_reason"].value_counts().to_dict()
facts["drought_drying_year_median"] = float(springs.loc[springs["drying_reason"] == "drought", "dried_year"].median())
print(cause); print("earthquake-dried springs that dried in 2015:", facts["earthquake_dried_in_2015"])

recent = springs[(springs["dried"] == 1) & (springs["dried_year"] >= 2000)]
tab = pd.crosstab(recent["dried_year"].astype(int), recent["drying_reason"])
order = [c for c in ["earthquake", "drought", "infrastructure", "neglect_or_disruption", "natural_disaster", "land_use", "unknown"] if c in tab.columns]
ax = tab[order].plot.bar(stacked=True, figsize=(11, 4.5), width=0.85, colormap="tab10")
ax.set_xlabel("Reported drying year (AD)"); ax.set_ylabel("Dried springs")
ax.set_title("Dried springs by reported drying year and reported cause (years 2000-2023)")
ax.legend(title="Reported cause", fontsize=8)
plt.tight_layout(); plt.savefig(FIGURES_DIR / "overview_drying_year_by_cause.png", dpi=300); plt.show()
""",
"""MD:
## Data-quality checks and climate grid cells
""",
"""
geo_cols = ["geometry", "buffer", "LU", "drying_reason"]
facts["quality"] = {
    "duplicate_coordinates": int(springs.duplicated(["Latitude", "Longitude"]).sum()),
    "identical_rows": int(springs.drop(columns=[c for c in geo_cols if c in springs]).duplicated().sum()),
    "slope_sin_min": float(springs["Slope_sin"].min()), "slope_sin_max": float(springs["Slope_sin"].max()),
    "slope_cos_max": float(springs["Slope_cos"].max()),
    "n_missing_formation": int(springs["Formation"].isna().sum()),
}
groups = grid_cell_ids(springs["Latitude"].values, springs["Longitude"].values)
per_cell = springs.assign(cell=groups).groupby("cell")["dried"].agg(["size", "mean"])
facts["grid"] = {"n_cells": int(per_cell.shape[0]), "springs_per_cell_min": int(per_cell["size"].min()),
                 "springs_per_cell_max": int(per_cell["size"].max()),
                 "dried_pct_per_cell_min": 100 * float(per_cell["mean"].min()),
                 "dried_pct_per_cell_max": 100 * float(per_cell["mean"].max()),
                 "cells_all_active": int((per_cell["mean"] == 0).sum())}
print(per_cell.sort_values("size", ascending=False))
facts["quality"], facts["grid"]
""",
"""MD:
## Descriptive terrain and road figures

Regenerated from `Full_Analysis_data.csv` so the figures in the report are reproducible.
""",
"""
colors = {"active": "#1f4e9c", "dried": "#d62728"}
cond = springs["Source Condition"].str.strip().str.lower()

# Elevation in 100 m bins
bins = np.arange(500, 2900, 100)
fig, ax = plt.subplots(figsize=(11, 4.5))
for i, c in enumerate(["active", "dried"]):
    counts, _ = np.histogram(springs.loc[cond == c, "Elev"], bins=bins)
    ax.bar(bins[:-1] + 25 + 50 * i, counts, width=48, color=colors[c], label=c)
ax.set_xticks(bins[:-1] + 50); ax.set_xticklabels([f"{b}-{b+100}" for b in bins[:-1]], rotation=60, fontsize=8)
ax.set_xlabel("Elevation (m)"); ax.set_ylabel("Springs"); ax.legend(title="Source condition")
ax.set_title("Spring condition across 100 m elevation bins")
plt.tight_layout(); plt.savefig(FIGURES_DIR / "overview_elevation_bins.png", dpi=300); plt.show()

bands = pd.cut(springs["Elev"], [0, 1000, 1400, 1700, 2000, 3000],
               labels=["<1000", "1000-1400", "1400-1700", "1700-2000", ">2000"])
by_band = springs.groupby(bands, observed=True)["dried"].agg(["size", "mean"])
facts["elevation"] = {"median": float(springs["Elev"].median()), "min": float(springs["Elev"].min()),
                      "max": float(springs["Elev"].max()),
                      "n_1400_1700": int(by_band.loc["1400-1700", "size"]),
                      "dried_pct_by_band": {str(k): 100 * float(v) for k, v in by_band["mean"].items()},
                      "springs_by_band": {str(k): int(v) for k, v in by_band["size"].items()}}
print(by_band)
""",
"""
aspect_classes = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
asp = springs[[f"Aspect-{a}" for a in aspect_classes]].astype(bool)
asp.columns = aspect_classes
klass = asp.idxmax(axis=1)
counts = pd.crosstab(klass, cond).reindex(aspect_classes)
share = 100 * counts["dried"] / counts.sum(axis=1)

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
x = np.arange(len(aspect_classes))
axes[0].bar(x - 0.2, counts["active"], 0.4, color=colors["active"], label="active")
axes[0].bar(x + 0.2, counts["dried"], 0.4, color=colors["dried"], label="dried")
axes[0].set_xticks(x); axes[0].set_xticklabels(aspect_classes); axes[0].set_ylabel("Springs")
axes[0].set_xlabel("Aspect class"); axes[0].legend(); axes[0].set_title("(a) Springs per aspect class")
axes[1].bar(x, share, color="#7f7f7f")
axes[1].axhline(100 * nd / n, color="k", ls="--", lw=1, label=f"all springs ({100*nd/n:.1f}%)")
axes[1].set_xticks(x); axes[1].set_xticklabels(aspect_classes); axes[1].set_ylabel("Dried springs (%)")
axes[1].set_xlabel("Aspect class"); axes[1].legend(); axes[1].set_title("(b) Share of springs that are dried")
plt.tight_layout(); plt.savefig(FIGURES_DIR / "overview_aspect.png", dpi=300); plt.show()
facts["aspect"] = {"counts": counts.to_dict(orient="index"), "dried_pct": share.round(2).to_dict()}

# Polar scatter: aspect (angle, compass) and elevation (radius)
fig = plt.figure(figsize=(7, 7)); ax = fig.add_subplot(projection="polar")
ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
for c in ["active", "dried"]:
    sub = springs[cond == c]
    ax.scatter(np.deg2rad(sub["Aspect"]), sub["Elev"], s=6, alpha=0.6, color=colors[c], label=c)
ax.set_title("Springs by aspect (angle) and elevation in m (radius)", pad=20)
ax.legend(loc="lower left", bbox_to_anchor=(-0.1, -0.1))
plt.tight_layout(); plt.savefig(FIGURES_DIR / "overview_elevation_aspect_polar.png", dpi=300); plt.show()
facts["aspect"]
""",
"""
road_cols = [f"Road-{a}" for a in aspect_classes]
means = springs.groupby(cond)[road_cols].mean().T
ax = means.plot.bar(figsize=(10, 4.5), color=[colors["active"], colors["dried"]], width=0.8)
ax.set_xlabel("Direction from spring"); ax.set_ylabel("Mean road crossings in 1 km buffer")
ax.set_title("Mean road crossings by direction within a 1 km buffer"); ax.legend(title="Source condition")
plt.xticks(rotation=0); plt.tight_layout()
plt.savefig(FIGURES_DIR / "overview_road_crossings.png", dpi=300); plt.show()
total = springs[road_cols].sum(axis=1)
facts["roads"] = {"mean_by_direction": means.round(4).to_dict(),
                  "directions_dried_higher": [d for d in road_cols if means.loc[d, "dried"] > means.loc[d, "active"]],
                  "mean_total_active": float(total[cond == "active"].mean()),
                  "mean_total_dried": float(total[cond == "dried"].mean())}
facts["roads"]
""",
"""MD:
## Springs outside the analysis set (future transfer test)

Springs in the 7-municipality inventory that are not among the 3,287 analysis springs,
and how many fall in ERA5-Land cells that are *not* used by any Roshi spring.
""",
"""
sp = raw[stype == "spring"].dropna(subset=["Latitude", "Longitude"]).copy()
outside = sp[~_coord_key(sp).isin(set(_coord_key(springs)))].copy()
outside["cell"] = grid_cell_ids(outside["Latitude"].values, outside["Longitude"].values)
outside["new_cell"] = ~outside["cell"].isin(set(groups))
outside["dried"] = outside["Source Condition"].astype(str).str.strip().str.lower().eq("dried")
tab = outside.groupby("Municipality").agg(springs=("cell", "size"), cells=("cell", "nunique"),
                                          pct_in_new_cells=("new_cell", lambda s: 100 * s.mean()),
                                          pct_dried=("dried", lambda s: 100 * s.mean()))
facts["outside"] = {"n_springs": int(len(outside)), "pct_in_new_cells": 100 * float(outside["new_cell"].mean()),
                    "by_municipality": tab.round(1).to_dict(orient="index")}
tab.round(1)
""",
"""MD:
## Size of the temporal augmentation proposed in the report (Section 6.5 of the submitted version)

Rows per active spring for years 2015-2023, rows per dried spring for its drying year to 2023
(drying year >= 1964 so a complete window exists).
""",
"""
years_active = list(range(2015, SURVEY_YEAR + 1))
dy_ok = dy[dy >= first_full_end]
aug_active = facts["n_active"] * len(years_active)
aug_dried = int((SURVEY_YEAR - dy_ok + 1).sum())
pre = int(sum(min(2014, SURVEY_YEAR) - y + 1 for y in dy_ok if y <= 2014))
facts["augmentation"] = {"rows_per_active": len(years_active), "rows_active": aug_active, "rows_dried": aug_dried,
                         "pct_dried_after": 100 * aug_dried / (aug_active + aug_dried),
                         "dried_rows_before_2015": pre, "pct_dried_rows_before_2015": 100 * pre / aug_dried}
save_json(facts, "dataset_facts.json")
facts["augmentation"]
""",
]

# ---------------------------------------------------------------- 01 climate features
NB01 = [
"""MD:
# 01 - ERA5-Land climate features (Version A and Version B)

For every spring: the 15-year mean and Mann-Kendall Sen's slope of 2 m temperature, 2 m dewpoint,
total precipitation (mm/yr) and potential evaporation (mm/yr, positive), from the nearest
ERA5-Land 0.1 deg cell.

* **Version A** (label-conditional): active springs use 2009-2023; dried springs use the 15 years
  ending at their own drying year. This leaks the label and is kept only to document Models 1-2.
* **Version B** (fixed): every spring uses 2009-2023 (the survey year is 2023).
""",
BOOT,
"""
import xarray as xr
from spring_drying.climate import (FEATURE_COLS, cell_annual_series, fixed_window_features,
                                   label_conditional_features, grid_cell_ids)

springs = load_springs()
lat, lon = springs["Latitude"].values, springs["Longitude"].values
with xr.open_dataset(NC_PATH) as ds:
    era5 = {"lat_res": float(abs(ds.latitude.values[1] - ds.latitude.values[0])),
            "first_month": str(pd.Timestamp(ds.valid_time.values[0]).date()),
            "last_month": str(pd.Timestamp(ds.valid_time.values[-1]).date()),
            "n_months": int(ds.sizes["valid_time"]), "variables": list(ds.data_vars),
            "lat_min": float(ds.latitude.min()), "lat_max": float(ds.latitude.max()),
            "lon_min": float(ds.longitude.min()), "lon_max": float(ds.longitude.max())}
era5
""",
"""
version_a = label_conditional_features(lat, lon, springs["dried"].values, springs["dried_year"].values)
version_b = fixed_window_features(lat, lon)
version_a.to_csv(TABLES_DIR / "climate_features_version_a.csv", index=False)
version_b.to_csv(TABLES_DIR / "climate_features_version_b.csv", index=False)

dried = springs["dried"] == 1
missing_year = dried & springs["dried_year"].isna()
too_early = dried & (springs["dried_year"] < ERA5_LAND_FIRST_YEAR + WINDOW_LEN - 1)
facts = {"era5": era5, "window": f"{WINDOW_END - WINDOW_LEN + 1}-{WINDOW_END}",
         "version_a_valid_rows": int(version_a.notna().all(axis=1).sum()),
         "version_a_missing_year": int(missing_year.sum()), "version_a_too_early": int(too_early.sum()),
         "n_cells": int(len(np.unique(grid_cell_ids(lat, lon)))),
         "version_b_distinct_vectors": int(version_b.round(9).drop_duplicates().shape[0]),
         "version_a_distinct_vectors": int(version_a.dropna().round(9).drop_duplicates().shape[0])}
facts
""",
"""
annual, cells = cell_annual_series(lat, lon)
regional = annual.groupby(level="year").mean()
fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
axes[0].plot(regional.index, regional["t2m"], color="#d62728")
axes[0].axvspan(WINDOW_END - WINDOW_LEN + 0.5, WINDOW_END + 0.5, color="#1f77b4", alpha=0.15,
                label=f"Fixed window (Version B) {WINDOW_END - WINDOW_LEN + 1}-{WINDOW_END}")
axes[0].set_ylabel("Annual mean 2 m temperature (deg C)")
axes[0].set_title("ERA5-Land annual temperature averaged over the 12 cells containing Roshi springs")
axes[0].legend(loc="upper left")
dy = springs.loc[dried, "dried_year"].dropna()
axes[1].hist(dy, bins=np.arange(1940, 2025), color="#8c564b")
axes[1].axvline(WINDOW_END, color="#1f77b4", ls="--", lw=1.5, label="window end for every active spring (Version A)")
axes[1].set_ylabel("Dried springs"); axes[1].set_xlabel("Year (AD)"); axes[1].legend(loc="upper left")
axes[1].set_title("Reported drying year = window end for dried springs under Version A")
plt.tight_layout(); plt.savefig(FIGURES_DIR / "climate_timeseries_windows.png", dpi=300); plt.show()
facts["warming_1950s_to_2010s"] = float(regional.loc[2010:2019, "t2m"].mean() - regional.loc[1950:1959, "t2m"].mean())
facts["warming_1950s_to_2010s"]
""",
"""
LABELS = {"Dewpoint_rate": "Dewpoint trend (deg C/yr)", "Temperature_rate": "Temperature trend (deg C/yr)",
          "Precipitation_rate": "Precipitation trend (mm/yr per yr)", "Evaporation_rate": "Potential evaporation trend (mm/yr per yr)",
          "Dewpoint_mean": "Dewpoint mean (deg C)", "Temperature_mean": "Temperature mean (deg C)",
          "Precipitation_mean": "Precipitation mean (mm/yr)", "Evaporation_mean": "Potential evaporation mean (mm/yr)"}

def plot_distributions(feat, title, fname):
    fig, axes = plt.subplots(4, 2, figsize=(11, 12)); axes = axes.ravel()
    for ax, col in zip(axes, FEATURE_COLS):
        valid = feat[col].notna()
        edges = np.histogram_bin_edges(feat.loc[valid, col], bins=20)
        width = (edges[1] - edges[0]) * 0.4
        for off, (c, color) in zip((-0.5, 0.5), (("active", "#2E7D32"), ("dried", "#8D6E63"))):
            vals = feat.loc[valid & ((springs["dried"] == 1) == (c == "dried")), col]
            counts, _ = np.histogram(vals, bins=edges)
            ax.bar((edges[:-1] + edges[1:]) / 2 + off * width, 100 * counts / len(vals), width=width,
                   color=color, alpha=0.8, label=c, edgecolor="black", linewidth=0.4)
        ax.set_xlabel(LABELS[col]); ax.set_ylabel("Springs in class (%)"); ax.legend(fontsize=8)
    fig.suptitle(title, fontsize=13)
    plt.tight_layout(rect=[0, 0, 1, 0.98]); plt.savefig(FIGURES_DIR / fname, dpi=300); plt.show()

plot_distributions(version_a, "Version A (label-conditional window): climate features by spring condition",
                   "climate_distribution_version_a.png")
plot_distributions(version_b, f"Version B (fixed {WINDOW_END - WINDOW_LEN + 1}-{WINDOW_END} window): climate features by spring condition",
                   "climate_distribution_version_b.png")

def medians(feat):
    return {c: {"active": float(feat.loc[springs["dried"] == 0, c].median()),
                "dried": float(feat.loc[springs["dried"] == 1, c].median())} for c in FEATURE_COLS}
facts["medians_version_a"] = medians(version_a)
facts["medians_version_b"] = medians(version_b)
pd.DataFrame({k: {f"{c}_{g}": v for c, d in facts[k].items() for g, v in d.items()} for k in ["medians_version_a", "medians_version_b"]})
""",
"""
corr = version_b.corr()
plt.figure(figsize=(8, 6.5))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, vmin=-1, vmax=1)
plt.title(f"Correlation of Version B climate features ({WINDOW_END - WINDOW_LEN + 1}-{WINDOW_END})")
plt.tight_layout(); plt.savefig(FIGURES_DIR / "climate_correlation_version_b.png", dpi=300); plt.show()
save_json(facts, "climate_facts.json")
""",
]

# ---------------------------------------------------------------- shared prefix for models
MODEL_PREFIX = BOOT + r"""
from spring_drying.climate import FEATURE_COLS
from spring_drying.modeling import make_rf, make_model3
from spring_drying.experiments import run_experiment, print_result

springs = load_springs()
base = springs.drop(columns=FEATURE_COLS + ["Perennial / Seasonal"])  # CSV climate columns unused; text label replaced by 0/1
ASPECT = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
ROADS = [f"Road-{a}" for a in ASPECT]
ASPECT_1HOT = [f"Aspect-{a}" for a in ASPECT]
"""

NB02 = [
"""MD:
# 02 - Model 1: exploratory full-feature model (Version A climate)

29 predictors: spring type, elevation, aspect (degrees and 8 one-hot classes), 8 directional road
counts, Slope_sin/Slope_cos and the 8 Version A climate features. No VIF screening.

This is the corrected re-run of `archive/random_forest_model_detailed.ipynb`: that notebook cast every
feature to `int`, which set the dewpoint, temperature and evaporation trends, evaporation mean and
Slope_cos to zero. Here all features stay `float`. The slope pair is kept for fidelity but is
degenerate (Slope_sin ~ 1 for every spring, see notebook 00).
""",
MODEL_PREFIX,
"""
version_a = pd.read_csv(TABLES_DIR / "climate_features_version_a.csv")
data = pd.concat([base.reset_index(drop=True), version_a], axis=1).rename(columns={"perennial": "Perennial / Seasonal"})
features = ["Perennial / Seasonal", "Elev", "Aspect"] + ROADS + ASPECT_1HOT + ["Slope_sin", "Slope_cos"] + FEATURE_COLS
valid = data[features].notna().all(axis=1)
print(len(features), "features;", int(valid.sum()), "of", len(data), "springs have a complete Version A window")
result, model = run_experiment("model1_exploratory", "Model 1 (exploratory, Version A)",
                               data.loc[valid, features], data.loc[valid, "dried"].values, make_rf())
print_result(result)
""",
]

NB03 = [
"""MD:
# 03 - Model 2: refined feature set (Version A climate)

As described in the submitted report: Model 1 without land cover, geology (never in Model 1's matrix)
and evaporation, i.e. spring type, elevation, aspect (degrees + one-hot), the 8 road counts and the
6 non-evaporation Version A climate features. The degenerate slope pair is also left out.
The original Model 2 code was not archived; this notebook re-creates it from the report's description.
""",
MODEL_PREFIX,
"""
version_a = pd.read_csv(TABLES_DIR / "climate_features_version_a.csv")
data = pd.concat([base.reset_index(drop=True), version_a], axis=1).rename(columns={"perennial": "Perennial / Seasonal"})
climate = [c for c in FEATURE_COLS if not c.startswith("Evaporation")]
features = ["Perennial / Seasonal", "Elev", "Aspect"] + ROADS + ASPECT_1HOT + climate
valid = data[features].notna().all(axis=1)
print(len(features), "features;", int(valid.sum()), "springs")
result, model = run_experiment("model2_refined", "Model 2 (refined, Version A)",
                               data.loc[valid, features], data.loc[valid, "dried"].values, make_rf())
print_result(result)
""",
]

NB04 = [
"""MD:
# 04 - Model 3 with the Version A window (proposal predictors, leaky)

Exactly the proposal predictor set (8 climate features + spring type, VIF screening inside the
pipeline) but with the label-conditional Version A window. Its near-perfect score is the result that
prompted the leakage investigation. Re-run of `archive/random_forest_proposal_compliant_model.ipynb`
with the 2009-2023 survey-year window and shuffled cross-validation.
""",
MODEL_PREFIX,
"""
version_a = pd.read_csv(TABLES_DIR / "climate_features_version_a.csv")
data = pd.concat([base.reset_index(drop=True), version_a], axis=1).rename(columns={"perennial": "Perennial / Seasonal"})
features = FEATURE_COLS + ["Perennial / Seasonal"]
valid = data[features].notna().all(axis=1)
result, model = run_experiment("model3_version_a", "Model 3 with Version A window",
                               data.loc[valid, features], data.loc[valid, "dried"].values, make_model3())
print_result(result)
""",
]

NB05 = [
"""MD:
# 05 - Model 3 (final): fixed 2009-2023 window, comparisons, Model 3b and checks

* **Model 3**: the proposal predictors (8 climate features + spring type), VIF screening fitted on
  training springs only, Random Forest (2,000 trees, balanced class weights), stratified 70/30 split,
  shuffled 5-fold CV, and a leave-one-grid-cell-out ("new area") test.
* **Comparisons**: spring type only, climate only.
* **Model 3b**: label screening by the survey's reported cause - drought-dried vs active springs, with
  earthquake-dried vs active as a contrast.
* **Checks**: number of distinct feature rows, a lookup-table baseline, the effect of unshuffled CV,
  and the Version A leakage diagnostic (window end year as the only input).
""",
MODEL_PREFIX,
"""
from spring_drying.climate import grid_cell_ids

springs = attach_drying_reason(springs)
version_b = pd.read_csv(TABLES_DIR / "climate_features_version_b.csv")
data = pd.concat([springs[["dried", "drying_reason", "perennial", "dried_year"]].reset_index(drop=True), version_b], axis=1)
data = data.rename(columns={"perennial": "Perennial / Seasonal"})
groups = grid_cell_ids(springs["Latitude"].values, springs["Longitude"].values)
FEATURES = FEATURE_COLS + ["Perennial / Seasonal"]
X, y = data[FEATURES], data["dried"].values
print("springs", len(X), "| climate grid cells", len(set(groups)),
      "| distinct feature rows", X.round(9).drop_duplicates().shape[0])
""",
"""
model3, fitted3 = run_experiment("model3_final", "Model 3 (fixed window)", X, y, make_model3(),
                                 groups=groups, new_area=True)
print_result(model3)
pd.DataFrame({"impurity": model3["importance_impurity"], "permutation": model3["importance_permutation"]}).round(4)
""",
"""MD:
## Comparisons and Model 3b (label screening by drying cause)
""",
"""
active = data["dried"] == 0
configs = [
    ("cmp_type_only", "Spring type only", np.ones(len(data), bool), ["Perennial / Seasonal"], False),
    ("cmp_climate_only", "Climate only", np.ones(len(data), bool), FEATURE_COLS, False),
    ("model3b_drought", "Model 3b: drought-dried vs active", (active | (data["drying_reason"] == "drought")).values, FEATURES, True),
    ("model3b_drought_climate_only", "Model 3b, climate only", (active | (data["drying_reason"] == "drought")).values, FEATURE_COLS, False),
    ("cmp_earthquake", "Contrast: earthquake-dried vs active", (active | (data["drying_reason"] == "earthquake")).values, FEATURES, False),
]
results = {"model3_final": model3}
for name, title, mask, cols, figs in configs:
    res, _ = run_experiment(name, title, data.loc[mask, cols], data.loc[mask, "dried"].values, make_model3(),
                            groups=groups[mask], new_area=True, make_figures=figs)
    results[name] = res
    print_result(res)

order = ["cmp_type_only", "cmp_climate_only", "model3_final", "model3b_drought", "model3b_drought_climate_only", "cmp_earthquake"]
summary = pd.DataFrame([{"configuration": results[k]["title"], "n_springs": results[k]["n_rows"], "n_dried": results[k]["n_dried"],
                         **results[k]["test"], "cv_f1_mean": results[k]["cv"]["f1_mean"], "cv_f1_sd": results[k]["cv"]["f1_sd"],
                         "cv_auc_mean": results[k]["cv"]["auc_mean"], "cv_auc_sd": results[k]["cv"]["auc_sd"],
                         "new_area_auc": results[k]["new_area_auc"]} for k in order]).set_index("configuration")
summary.round(4).to_csv(TABLES_DIR / "model3_final_summary.csv")
summary.round(3)
""",
"""
plot = summary[["roc_auc", "cv_auc_mean", "new_area_auc"]].rename(columns={
    "roc_auc": "Test set (70/30)", "cv_auc_mean": "5-fold CV (shuffled)", "new_area_auc": "New area (leave-one-grid-cell-out)"})
ax = plot.plot.barh(figsize=(10, 5.5), width=0.8, color=["#1f77b4", "#6baed6", "#fd8d3c"])
ax.axvline(0.5, color="k", ls="--", lw=1, label="Chance (0.5)")
ax.set_xlim(0.3, 1.0); ax.set_xlabel("ROC-AUC"); ax.set_ylabel(""); ax.invert_yaxis()
ax.set_title(f"Model 3, comparisons and Model 3b (climate window {WINDOW_END - WINDOW_LEN + 1}-{WINDOW_END})")
ax.legend(loc="lower right", fontsize=9)
plt.tight_layout(); plt.savefig(FIGURES_DIR / "model3_comparison.png", dpi=300); plt.show()
""",
"""MD:
## Checks: lookup-table baseline, unshuffled CV, and the Version A leakage diagnostic
""",
"""
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import roc_auc_score
from sklearn.ensemble import RandomForestClassifier
from spring_drying.evaluation import holdout_metrics

checks = {}
# 1) Lookup table: dried rate of each distinct feature row, learned on the training springs only
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, stratify=y, random_state=RANDOM_STATE)
key = lambda d: d.round(9).astype(str).agg("|".join, axis=1)
rate = pd.Series(y_tr).groupby(key(X_tr).values).mean()
p = key(X_te).map(rate).fillna(y_tr.mean()).values
checks["lookup_table_auc"] = float(roc_auc_score(y_te, p))
checks["test_rows_seen_in_train_pct"] = 100 * float(key(X_te).isin(set(key(X_tr))).mean())
checks["n_distinct_rows"] = int(X.round(9).drop_duplicates().shape[0])

# 2) The submitted report's CV: 5 folds in file order (no shuffling)
unshuffled = cross_val_score(make_model3(), X, y, cv=5, scoring="f1")
checks["cv_f1_unshuffled_mean"], checks["cv_f1_unshuffled_sd"] = float(unshuffled.mean()), float(unshuffled.std())
checks["cv_f1_unshuffled_folds"] = [float(v) for v in unshuffled]
checks["dried_pct_by_file_fifth"] = [100 * float(c.mean()) for c in np.array_split(y, 5)]

# 3) Version A leakage diagnostic: the end year of each spring's Version A window as the ONLY input
window_end = data["dried_year"].where(data["dried"] == 1, WINDOW_END)
diag = pd.DataFrame({"window_end_year": window_end, "dried": data["dried"]}).dropna()
d_tr, d_te, dy_tr, dy_te = train_test_split(diag[["window_end_year"]], diag["dried"], test_size=0.3,
                                            stratify=diag["dried"], random_state=RANDOM_STATE)
rf = RandomForestClassifier(n_estimators=500, class_weight="balanced", random_state=RANDOM_STATE).fit(d_tr, dy_tr)
checks["leakage_diagnostic"] = {k: float(v) for k, v in holdout_metrics(dy_te, rf.predict(d_te), rf.predict_proba(d_te)[:, 1]).items()}
checks["n_dried_ending_in_survey_year"] = int(((data["dried"] == 1) & (data["dried_year"] == WINDOW_END)).sum())
save_json(checks, "model3_checks.json")
checks
""",
]

if __name__ == "__main__":
    for fname, cells in [("00_dataset_overview.ipynb", NB00), ("01_climate_features.ipynb", NB01),
                         ("02_model1_exploratory.ipynb", NB02), ("03_model2_refined.ipynb", NB03),
                         ("04_model3_version_a.ipynb", NB04), ("05_model3_final.ipynb", NB05)]:
        nbf.write(notebook(cells), NB_DIR / fname)
        print("wrote", NB_DIR / fname)
