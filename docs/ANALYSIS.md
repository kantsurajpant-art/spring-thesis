# Project status, bugs and recommended approach

*Review date: 2026-10-04. All numbers were reproduced against the data in `../Project Preperation Rough/`.*

## 1. Status

| Component | State |
|---|---|
| ERA5-Land download (1950–2026, 0.1°) | ✅ done |
| Spring inventory, DEM, roads, geology and LULC merged into `Full_Analysis_data.csv` | ✅ done, but the **code that produced it is not in this repo** and cannot be re-run |
| Climate feature extraction (notebook 1) | ⚠ runs, but the window design leaks the label and the result is never saved |
| Fixed-window climate features (notebook 4) | ✅ correct, saved to `results/tables/` |
| RF models | 3 variants. Only #4 is methodologically defensible, and its evaluation is still optimistic |
| Spatial validation, tests, version control, pinned environment | ❌ missing, now scaffolded in this repo |

**Valid headline result today:** fixed-window RF on the proposal predictors. With a random split, test F1 = 0.48 and ROC-AUC = 0.75.
With leave-one-grid-cell-out CV and the corrected 2009–2023 window, **ROC-AUC = 0.60**, and **climate alone scores 0.54**, close to chance. The perennial/seasonal attribute carries most of
the signal: 59 % of seasonal springs are dried, against 16 % of perennial ones.

## 2. Bugs and inconsistencies (most severe first)

### Critical: invalidates reported results

1. **The climate window is chosen by the label** (notebook 1, `get_slopes`, cell 10). Active springs use 2011–2025 and dried springs use the 15 years before
   drying. The window period alone predicts the label perfectly (notebook 4, cell 19: AUC = 1.0). The F1 ≈ 0.99 of notebooks 2 and 3 is therefore an artefact.
2. **The climate features have only 12 distinct values.** All 3,287 springs fall into 12 ERA5-Land 0.1° (~11 km) grid cells, so the "climate" columns act
   as a 12-level location ID. Every spring in a cell shares identical climate values, and a random train/test split puts springs from the same cell on
   both sides. The effective sample size for any climate–drying relationship is **12, not 3,287**.
3. **`X = maindata.drop(...).astype(int)`** (notebook 2, cell 21) truncates every fractional feature: Dewpoint/Temperature/Evaporation rates,
   Evaporation_mean and Slope_cos all become 0, and Aspect loses its decimals. The exploratory model and its feature-importance figure are wrong.

### High

3a. **The window end year is wrong.** Active springs use a window ending in **2025**, but the inventory was surveyed between Sep 2023 and early 2024, and the
    latest drying year is 2023. "Active" therefore describes status as of 2023, and 2024–2025 climate is post-survey information. The window should
    be 2009–2023 (`config.SURVEY_YEAR`). Raw drying years are in Bikram Sambat (e.g. 2072 BS ≈ 2015 AD). The analysis CSV holds the converted AD years.
    One raw entry is the typo `20723`.

4. **The slope feature is broken upstream.** `Slope_sin` is 0.99999–1.0 and `Slope_cos` is ~1e-5 for every spring, which implies a slope of about 90° everywhere.
   The typical cause is computing slope on a DEM in geographic (degree) coordinates without metre scaling, or a degree/radian mix-up. The feature carries no information.
5. **Notebook 1 never saves what it computes.** Cell 24 reloads `Full_Analysis_data.csv` over `static_csv`, and cell 26 writes that reloaded table back
   unchanged. Notebook 1 also *reads* its spring list from the same file it is meant to produce. The climate columns in the CSV therefore come from
   an earlier, unrecorded run, and the pipeline is circular and not reproducible.
6. **The 1946 cutoff contradicts the data**, which starts in 1950. Springs that dried between 1946 and 1964 (3 springs) get partial windows with fewer than 15 years,
   so their Mann-Kendall slopes rest on fewer points. The cutoff should be 1964 (`ERA5_LAND_FIRST_YEAR + 14`).
7. **4 springs labelled `dried` have no drying year**, so `get_slopes` silently treats them as active and gives them the 2011–2025 window.
8. **Duplicates:** 51 springs share exact coordinates with another spring, and 36 rows are identical on all features. They leak between train and test.

### Medium / low

9. **Inconsistent units.** `tp` is converted to mm/yr, but `pev` stays in m/day with the ECMWF sign (negative = evaporation). Evaporation_mean is therefore about
   −0.004 and Evaporation_rate about 1e-5, which is hard to read and to plot. (`src/spring_drying/climate.py` returns both in mm/yr, with evaporation positive.)
10. The column `Dried since how many years?` holds a **calendar year** (for example 2017), not a duration.
11. The index column is dropped by position (`.iloc[:, 1:]`, notebooks 1 and 2). Notebook 1 now saves with `index=False`, so re-reading that output this
    way would silently drop `Latitude`. Drop columns by name instead.
12. `cross_val_score(cv=5)` does not shuffle. Fold F1 ranges from 0.83 to 0.99 (notebook 2) and from 0.17 to 0.45 (notebook 4), which shows the score depends on row order.
13. VIF screening is computed on the full dataset before the split (a minor leak). `StandardScaler` does nothing for a random forest. `LabelEncoder` on an already 0/1
    target is redundant. Mann-Kendall p-values are computed and then discarded, which doubles the runtime.
14. Impurity-based feature importance is biased toward continuous, high-cardinality features. Use permutation importance on held-out data.
15. **Possible circularity in `Perennial / Seasonal`:** if the survey recorded a spring that has since dried as "seasonal", this predictor partly encodes the outcome.
    Check the field protocol before relying on it.
16. Housekeeping: the `../` data paths were broken because the data had moved (now fixed through `config.py`). The saved outputs show the notebooks
    were last run from `C:\Users\kants\Desktop\…`, a different copy. The data CSV exists twice (`Project Preperation Rough/` and `9-credit Project/`).

## 3. Recommended approach

### 3.1 Fix the science first

The core question is whether climate exposure explains spring drying. A cross-sectional spring-level classifier cannot answer it with ~11 km climate
data covering 12 cells. Options, best first:

1. **Survival (time-to-drying) model.** This uses the drying year correctly instead of leaking it. Each spring is followed year by year from a start
   year; dried springs have an event at their drying year, and active springs are right-censored at 2025. Fit a discrete-time hazard model
   (logistic regression on spring-years) or a Cox model with **time-varying annual climate anomalies** (precipitation deficit, SPEI, temperature anomaly)
   and cell fixed effects or stratification. The question then becomes "do dry or hot years raise the drying hazard?", which is answerable
   even with 12 cells, because the variation is over time.
2. **Higher-resolution climate.** Use CHELSA or WorldClim (~1 km), or CHIRPS precipitation (0.05°). Alternatively, downscale ERA5-Land temperature to each
   spring using the DEM elevation and a lapse rate (about −6.5 °C/km). Either gives real spring-to-spring climate variation.
3. **If the proposal scope must stay as it is,** report the fixed-window model with spatially grouped CV, and state openly that climate is near-constant
   within a cell and that drying varies mostly within cells. That points to local, non-climate drivers (geology, land use, roads,
   groundwater abstraction), which is itself a defensible thesis finding.

### 3.2 Evaluation

- Use spatially blocked CV (`LeaveOneGroupOut` or `GroupKFold` over grid cells or spatial clusters). See `src/spring_drying/evaluation.py`.
- De-duplicate springs before splitting.
- Report PR-AUC and balanced accuracy alongside ROC-AUC, because the classes are imbalanced (22 % dried).
- Use permutation importance, and partial dependence for interpretation.
- Run feature screening (VIF) inside the CV folds, or on training data only.

### 3.3 Engineering

- **One pipeline, one source of truth:** raw inputs are read-only, and derived features are written to `results/tables/` by code in `src/`. Notebooks then become
  thin reports that call `src` functions, with no copy-pasted extraction logic.
- **Recover the missing upstream code** (DEM slope and aspect, road buffers, geology and LULC joins) into `src/` so that `Full_Analysis_data.csv` can be regenerated.
- **Version control:** git with a private GitHub remote. Keep data out of git and record a SHA-256 manifest of the raw files, or use DVC.
- **Reproducibility:** pinned `requirements.txt` (done), fixed random seeds (done), `nbstripout` or "restart & run all" before committing.
- **Tests:** small pytest cases for unit conversion, window selection (complete 15 years, cutoff year), and the label encoding.
