"""Build the A-Z study and defence guide (report/Defense_Guide_AZ.docx).

All numbers come from report/numbers.json (the same source as the report), so the guide
and the report always agree. Usage (from the repo root):  python scripts/build_defense_guide.py
"""
import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
N = json.loads((ROOT / "report" / "numbers.json").read_text(encoding="utf-8-sig"))

f = N["facts"]; c = N["climate"]; k = N["checks"]
m1, m2, m3va, m3, m3b, m3bc = N["m1"], N["m2"], N["m3va"], N["m3"], N["m3b"], N["m3bc"]
typ, clim, eq = N["type"], N["climate"] and N["clim"], N["eq"]
cm = m3["confusion"]
win = c["window"].replace("-", " to ")
leak_lo = min(m1["test"]["roc_auc"], m2["test"]["roc_auc"], m3va["test"]["roc_auc"])
leak_hi = max(m1["test"]["roc_auc"], m2["test"]["roc_auc"], m3va["test"]["roc_auc"])
perennial_imp = 100 * m3["importance_impurity"]["Perennial / Seasonal"]
perennial_perm = m3["importance_permutation"]["Perennial / Seasonal"]
climate_perm_max = max(abs(v) for kk, v in m3["importance_permutation"].items() if kk != "Perennial / Seasonal")
all_active_acc = (cm["tn"] + cm["fp"]) / m3["n_test"]
eq_share = 100 * f["drying_cause"]["earthquake"] / f["n_dried"]
d = lambda x: f"{x:.3f}"  # noqa: E731
ci = lambda m, key="roc_auc": f"{d(m['test_ci'][key][0])} to {d(m['test_ci'][key][1])}"  # noqa: E731


# ------------------------------------------------------------------ content
SUMMARY = [
    f"The question: can a machine-learning model tell which springs in the Roshi Khola watershed have dried, using "
    f"climate data and one basic fact about each spring (perennial or seasonal)?",
    f"The data: {f['n_springs']:,} springs from ICIMOD's community inventory ({f['n_dried']} dried, {f['n_active']:,} active), "
    f"surveyed between {f['survey_dates']['p05']} and {f['survey_dates']['p95']} (5th to 95th percentile of record dates). "
    f"Climate comes from ERA5-Land: for each spring, the 15-year average and the trend (Sen's slope) of temperature, "
    f"dewpoint, rainfall and potential evaporation.",
    f"The twist: the first models scored ROC-AUC {d(leak_lo)} to {d(leak_hi)}, which is too good to be true. Dried springs "
    f"had climate taken from the 15 years before they dried, active springs from {win}. The model learned which years the "
    f"numbers came from, not climate. Proof: the window end year alone predicts the label with ROC-AUC "
    f"{d(k['leakage_diagnostic']['roc_auc'])}. This is data leakage.",
    f"The fix and the real result: every spring gets the same window ({win}). Model 3 then scores accuracy "
    f"{d(m3['test']['accuracy'])}, F1 {d(m3['test']['f1'])}, ROC-AUC {d(m3['test']['roc_auc'])} on unseen test springs, "
    f"and a cross-validated F1 of {d(m3['cv']['f1_mean'])} ± {d(m3['cv']['f1_sd'])}.",
    f"The extra insight: {f['drying_cause']['earthquake']} dried springs were blamed on the earthquake and "
    f"{f['drying_cause']['drought']} on drought. Comparing only drought-dried springs with active springs (Model 3b) "
    f"raises ROC-AUC to {d(m3b['test']['roc_auc'])}, so the climate signal is real but diluted by non-climatic drying.",
    f"The honest limit: all springs fall in only {f['grid']['n_cells']} climate grid cells, so climate behaves like a "
    f"location code. When whole cells are hidden from training, ROC-AUC falls to {d(m3['new_area_auc'])}. "
    f"The dissertation will fix this with finer climate data and a year-by-year design.",
]

# (term, meaning, in this project)
GLOSSARY = {
    "A": [
        ("Accuracy", "Share of all predictions that are correct: (TP + TN) / all.",
         f"Model 3: {d(m3['test']['accuracy'])}. Misleading on its own: a model that calls every test spring 'active' "
         f"would score {all_active_acc:.3f} and find no dried springs."),
        ("AD / BS (calendars)", "AD is the Gregorian year; BS (Bikram Sambat) is the Nepali calendar, about 57 years ahead.",
         f"The raw survey stores drying years in BS. They were converted to AD; for {f['bs_to_ad_offset']['57']} of "
         f"{f['drying_year']['n_with_year']} dated springs the difference is exactly 57 years."),
        ("Aspect", "The compass direction a slope faces (N, NE, E, ...).",
         f"Dried share is lowest on E and NE slopes ({f['aspect']['dried_pct']['E']:.1f}%, {f['aspect']['dried_pct']['NE']:.1f}%) "
         f"and highest on SW, S, W ({f['aspect']['dried_pct']['SW']:.1f}%, {f['aspect']['dried_pct']['S']:.1f}%, "
         f"{f['aspect']['dried_pct']['W']:.1f}%). Descriptive only; not a predictor in Model 3."),
        ("AUC (ROC-AUC)", "Area under the ROC curve. The chance that a randomly picked dried spring gets a higher "
         "'risk of drying' score than a randomly picked active spring. 0.5 = coin toss, 1.0 = perfect.",
         f"Model 3: {d(m3['test']['roc_auc'])} (test), {d(m3['cv']['auc_mean'])} (cross-validation), "
         f"{d(m3['new_area_auc'])} (new areas). Main score used to compare models."),
        ("Augmentation (temporal)", "Creating extra training rows from existing data.",
         f"The submitted report proposed one row per spring per year. It would only raise the dried share from "
         f"{f['pct_dried']:.1f}% to {f['augmentation']['pct_dried_after']:.1f}% and would re-create leakage "
         f"({f['augmentation']['dried_rows_before_2015']:,} dried rows before 2015, where no active rows exist)."),
    ],
    "B": [
        ("Balanced class weight", "Training setting that makes each example of the rarer class count more.",
         f"Each dried spring counts about {f['n_active'] / f['n_dried']:.1f} times as much as an active spring."),
        ("Baseline", "A simple reference result that a model must beat to be useful.",
         f"Spring type alone: ROC-AUC {d(typ['test']['roc_auc'])}; climate alone {d(clim['test']['roc_auc'])}; "
         f"together (Model 3) {d(m3['test']['roc_auc'])}."),
        ("Bootstrap sample", "A random sample drawn with replacement; each Random Forest tree is trained on a different one.",
         "Gives the 2,000 trees slightly different views of the training data."),
    ],
    "C": [
        ("Class imbalance", "One class is much rarer than the other.",
         f"{f['pct_dried']:.1f}% of springs are dried. That is why accuracy is not enough and why class weights are used."),
        ("Classification (binary)", "Predicting one of two labels.", "Label 1 = dried, 0 = active."),
        ("Climate window", "The block of years over which climate averages and trends are computed.",
         f"15 years. Version A (leaky): ends at the drying year for dried springs. Version B (correct): {win} for everyone."),
        ("CMIP6 / SSP scenarios", "Global climate model projections under Shared Socioeconomic Pathways (e.g. SSP2-4.5 moderate, SSP5-8.5 high emissions).",
         "Planned for the dissertation (future drying risk), not done in this project."),
        ("Confusion matrix", "2 x 2 table of correct and wrong predictions per class.",
         f"Model 3 test: {cm['tn']} active correct, {cm['fp']} active wrongly called dried, {cm['tp']} dried found, "
         f"{cm['fn']} dried missed."),
        ("Cross-validation (k-fold)", "Split data into k parts; each part takes a turn as the test set; average the k scores.",
         f"Shuffled stratified 5-fold. Model 3 F1 {d(m3['cv']['f1_mean'])} ± {d(m3['cv']['f1_sd'])}. Without shuffling "
         f"(submitted version) it was {d(k['cv_f1_unshuffled_mean'])} ± {d(k['cv_f1_unshuffled_sd'])}, because the file is ordered."),
    ],
    "D": [
        ("Data leakage (target leakage)", "When the inputs secretly contain the answer, so the model scores well for the wrong reason.",
         f"Version A windows were set by the drying year. The window end year alone gives ROC-AUC "
         f"{d(k['leakage_diagnostic']['roc_auc'])}. Fixed by using the same window for all springs."),
        ("Decision tree", "A flowchart of yes/no questions on the features that ends in a prediction.",
         "A Random Forest is 2,000 of these voting together."),
        ("DEM (Digital Elevation Model)", "A grid of ground heights.", "SRTM DEM: elevation, slope, aspect (context only)."),
        ("Dewpoint", "Temperature at which air becomes saturated; a measure of humidity.",
         "`Dewpoint_mean` was removed by VIF (almost a copy of temperature); `Dewpoint_rate` was kept."),
        ("Distinct feature rows", "How many different input combinations exist.",
         f"Only {k['n_distinct_rows']} for {f['n_springs']:,} springs ({f['grid']['n_cells']} cells x 2 spring types)."),
        ("Drying cause (reported)", "The survey's 'Reason of drying' field.",
         f"Earthquake {f['drying_cause']['earthquake']}, drought {f['drying_cause']['drought']}, infrastructure "
         f"{f['drying_cause']['infrastructure']}, neglect/disruption {f['drying_cause']['neglect_or_disruption']}, "
         f"natural disaster {f['drying_cause']['natural_disaster']}, land use {f['drying_cause']['land_use']}, unknown {f['drying_cause']['unknown']}."),
    ],
    "E": [
        ("Earthquake (2015 Gorkha)", "Major earthquake in Nepal in April 2015 that disturbed groundwater paths.",
         f"{f['earthquake_dried_in_2015']} of {f['drying_cause']['earthquake']} earthquake-attributed springs dried in 2015 "
         f"({eq_share:.1f}% of all dried springs are earthquake-attributed). Climate cannot explain these."),
        ("ERA5 / ERA5-Land", "ECMWF reanalysis: physics-based reconstruction of past weather on a grid. ERA5-Land is the land "
         "version at about 9 km (0.1°).",
         f"Monthly data {c['era5']['first_month'][:7]} to {c['era5']['last_month'][:7]}. The springs fall in only "
         f"{f['grid']['n_cells']} cells."),
        ("Evaporation (potential)", "How much water the air could evaporate if water were available (evaporative demand).",
         "Converted to mm/year and made positive (ECMWF stores it as negative)."),
    ],
    "F": [
        ("F1-score", "Balance of precision and recall: 2·P·R / (P + R). Low if either is low.",
         f"Model 3: {d(m3['test']['f1'])}. Falls when the positive class is rare (Model 3b: {d(m3b['test']['f1'])})."),
        ("False positive / false negative", "FP: active spring wrongly called dried. FN: dried spring missed.",
         f"Model 3: FP {cm['fp']}, FN {cm['fn']}."),
        ("Feature (predictor)", "An input column the model uses.",
         "Model 3: 6 climate features after VIF + perennial/seasonal."),
        ("Feature importance", "How much the model relies on each feature (see Impurity and Permutation importance).",
         f"Spring type: {perennial_imp:.1f}% of impurity importance."),
    ],
    "G": [
        ("Generalisability / transferability", "Whether a model works in places or times it was not trained on.",
         f"Tested with the new-area test (ROC-AUC {d(m3['new_area_auc'])}). Panchkhal test planned for the dissertation."),
        ("Grid cell", "One square of the climate grid (about 9 to 11 km). Every spring inside gets the same climate values.",
         f"{f['grid']['n_cells']} cells, from {f['grid']['springs_per_cell_min']} to {f['grid']['springs_per_cell_max']:,} springs per cell."),
        ("Groundwater potential mapping", "Predicting where groundwater or springs are likely to occur (a different task from yours).",
         "Used only as a rough comparison (Upadhyaya et al. 2024; Al-Shabeeb et al. 2023)."),
    ],
    "H": [
        ("Held-out test set", "Data hidden from training and used once at the end to score the model.",
         f"30% of springs: {m3['n_test']} ({m3['n_test_dried']} dried)."),
        ("Hyperparameter", "A setting chosen before training (not learned from data).",
         "2,000 trees, balanced class weights, random_state 42. No tuning in this phase."),
    ],
    "I": [
        ("ICIMOD", "International Centre for Integrated Mountain Development.", "Provided the community spring inventory."),
        ("Impurity importance", "Random Forest's built-in score: how much each feature reduces mixing of classes in the tree splits. "
         "Can be biased (Strobl et al. 2007).",
         f"Spring type {perennial_imp:.1f}%; each climate feature smaller."),
    ],
    "J": [
        ("Join (spatial join)", "Attaching information to points based on where they are (e.g. which polygon they fall in).",
         "Springs were assigned to the Roshi watershed and to geology polygons by spatial join."),
    ],
    "K": [
        ("K-fold", "See Cross-validation.", "k = 5."),
    ],
    "L": [
        ("Label (target)", "The answer the model learns to predict.", "dried = 1, active = 0."),
        ("Label screening", "Cleaning or filtering the labels so they match the question.",
         "Model 3b keeps only drought-dried springs (screening by cause). Persistence screening is planned."),
        ("Leave-one-grid-cell-out (new-area test)", "Hide all springs of one grid cell, train on the rest, predict the hidden cell; repeat for every cell.",
         f"Model 3: {d(m3['new_area_auc'])}; climate only: {d(clim['new_area_auc'])} (close to chance)."),
        ("Logistic regression", "A simple linear classifier that outputs a probability.", "Planned for the dissertation comparison."),
        ("Lookup-table baseline", "Predict each test spring with the dried rate of training springs that have exactly the same inputs.",
         f"ROC-AUC {d(k['lookup_table_auc'])}, the same as Model 3, which shows the model learns cell + spring type."),
        ("LULC", "Land use / land cover (forest, farmland, settlement...).", "Prepared for context; excluded as a predictor."),
    ],
    "M": [
        ("Machine learning", "Algorithms that learn patterns from examples instead of being programmed with rules.", "Random Forest classifier."),
        ("Mann-Kendall test", "A non-parametric test for a steady upward or downward trend over time.", "Used with Sen's slope for the 15-year trends."),
        ("Model 1 / 2 / 3 / 3b", "The model versions in the report.",
         f"1: 29 features, Version A (AUC {d(m1['test']['roc_auc'])}, leaky). 2: 25 features, Version A "
         f"(AUC {d(m2['test']['roc_auc'])}, leaky). 3 Version A: proposal predictors (AUC {d(m3va['test']['roc_auc'])}, leaky). "
         f"3: proposal predictors, fixed window (AUC {d(m3['test']['roc_auc'])}, main result). "
         f"3b: drought-dried vs active (AUC {d(m3b['test']['roc_auc'])})."),
        ("Multicollinearity", "Features that carry nearly the same information.", "Handled with VIF screening."),
    ],
    "N": [
        ("n_estimators", "Number of trees in the Random Forest.", "2,000."),
        ("NetCDF", "File format for gridded scientific data (lat x lon x time).", "The ERA5-Land download."),
        ("New-area test", "See Leave-one-grid-cell-out.", f"ROC-AUC {d(m3['new_area_auc'])} for Model 3."),
    ],
    "O": [
        ("One-hot encoding", "Turning a category into 0/1 columns (one per category).", "Aspect classes in Models 1 and 2."),
        ("Overfitting", "A model memorises training data and does worse on new data.",
         "The gap between random-split AUC and new-area AUC shows the model partly memorises location."),
    ],
    "P": [
        ("Perennial / seasonal", "Perennial springs flow all year; seasonal springs only part of the year.",
         f"{f['pct_dried_seasonal']:.1f}% of seasonal vs {f['pct_dried_perennial']:.1f}% of perennial springs are dried. "
         f"Strongest predictor. Possible risk: dried springs may have been recorded as seasonal."),
        ("Permutation importance", "Shuffle one feature in the test data and measure how much AUC drops.",
         f"Spring type: drop {perennial_perm:.3f}; any single climate feature: at most {climate_perm_max:.3f} (climate features "
         f"are redundant, so one can replace another)."),
        ("Pipeline", "Chained steps (VIF, scaler, Random Forest) fitted together.",
         "Ensures VIF is fitted only on training springs in every split."),
        ("Positive class", "The class you treat as 'yes'.", "Dried (1)."),
        ("Precision", "Of springs predicted dried, the share that really are dried: TP / (TP + FP).",
         f"Model 3: {d(m3['test']['precision'])}."),
        ("Prediction rate vs success rate (AUC)", "Success rate: AUC on the data used to build a map. Prediction rate: AUC on held-out data.",
         "Upadhyaya et al. (2024): success 0.65/0.80, prediction 0.60. Compare your test AUC with the prediction rate."),
    ],
    "Q": [
        ("Quality checks (data)", "Checks for duplicates, impossible values and missing data.",
         f"{f['quality']['duplicate_coordinates']} duplicate coordinates, {f['quality']['identical_rows']} identical rows "
         f"(removing the {k['test_dup_coords']} affected test springs leaves the test ROC-AUC at {d(k['test_auc_without_dups'])}); "
         f"Slope_sin is about 1 for every spring (slope feature unusable)."),
    ],
    "R": [
        ("Random Forest", "Many decision trees trained on bootstrap samples with random feature subsets; they vote.",
         "2,000 trees, balanced class weights (Breiman 2001)."),
        ("random_state = 42", "A fixed random seed so results repeat exactly.", "Used for every split, CV and model."),
        ("Reanalysis", "Past weather reconstructed by combining observations with a physical model.",
         "ERA5-Land; temperature is reliable, mountain precipitation is biased (Khadka et al. 2022; Lavers et al. 2022)."),
        ("Recall (sensitivity)", "Of truly dried springs, the share the model finds: TP / (TP + FN).",
         f"Model 3: {d(m3['test']['recall'])}; Model 3b: {d(m3b['test']['recall'])}."),
        ("ROC curve", "Plot of true-positive rate vs false-positive rate for every decision threshold.", "Its area is the AUC."),
        ("Reproducibility", "Anyone can re-run the code and get the same numbers.",
         "Numbered notebooks 00-05, fixed seeds, numbers.json, references verified against Crossref."),
    ],
    "S": [
        ("Sen's slope", "The median of the slopes between all pairs of years; a trend estimate that ignores outliers.",
         "The '_rate' features (e.g. °C per year)."),
        ("SHAP", "A method that explains each individual prediction feature by feature.", "Planned for the dissertation."),
        ("SMOTE", "Creates synthetic examples of the rare class.", "Not used (class weights used instead); must be applied inside training folds only."),
        ("Spatial autocorrelation", "Nearby places tend to be similar.",
         "Why random splits are optimistic here and why the new-area test is needed."),
        ("SRTM", "Shuttle Radar Topography Mission elevation data.", "Source of the DEM."),
        ("StandardScaler (z-score)", "Rescales each feature to mean 0, standard deviation 1.", "Kept for continuity; no effect on trees."),
        ("Stratified split", "Train and test keep the same class proportions.", f"About {f['pct_dried']:.0f}% dried in both."),
    ],
    "T": [
        ("Threshold", "Probability above which a spring is called dried.", "0.5 (default)."),
        ("Training / test set", "Training: examples the model learns from. Test: hidden examples for the final score.", "70% / 30%."),
        ("Trend", "Direction and speed of change over time.", "15-year Sen's slope per variable."),
        ("True positive / true negative", "TP: dried spring correctly called dried. TN: active spring correctly called active.",
         f"Model 3: TP {cm['tp']}, TN {cm['tn']}."),
    ],
    "U": [
        ("Unseen area", "A location the model never saw in training.", "Simulated by the leave-one-grid-cell-out test."),
    ],
    "V": [
        ("Validation", "Any check of performance on data not used for fitting.", "Test set, 5-fold CV, new-area test."),
        ("Version A / Version B", "The two climate-window designs.", f"A: label-conditional (leaky). B: fixed {win} (correct)."),
        ("VIF (variance inflation factor)", "1 / (1 - R²) from regressing one feature on the others. VIF > 10 means mostly redundant.",
         f"Model 3 removed Dewpoint_mean (VIF {m3['vif']['dropped'][0][1]:.1f}) and Evaporation_mean "
         f"(VIF {m3['vif']['dropped'][1][1]:.1f})."),
    ],
    "W": [
        ("Watershed", "The land area that drains to one river.", "Roshi Khola watershed, Kavrepalanchowk."),
    ],
    "X": [
        ("XGBoost", "A gradient-boosting algorithm: trees built one after another, each fixing the previous errors.",
         "Planned for the dissertation comparison (Chen and Guestrin 2016)."),
    ],
    "Y": [
        ("Year-by-year (discrete-time) design", "One row per spring per year while it flows; label 1 in the year it dries.",
         "Recommended replacement for the augmentation idea; uses year-to-year climate variation and avoids leakage."),
    ],
    "Z": [
        ("Z-score", "See StandardScaler.", "Also used inside the VIF calculation."),
    ],
}

NUMBERS = [
    ("Springs analysed (active / dried)", f"{f['n_springs']:,} ({f['n_active']:,} / {f['n_dried']})"),
    ("Raw survey records (springs / ponds)", f"{f['raw']['n_records']:,} ({f['raw']['n_springs']:,} / {f['raw']['n_ponds']})"),
    ("Dried share: perennial vs seasonal", f"{f['pct_dried_perennial']:.1f}% vs {f['pct_dried_seasonal']:.1f}%"),
    ("ERA5-Land grid cells containing springs", f"{f['grid']['n_cells']}"),
    ("Fixed climate window", win),
    ("Leakage diagnostic (window end year only)", f"ROC-AUC {d(k['leakage_diagnostic']['roc_auc'])}"),
    ("Version A models (Models 1, 2, 3-VA) ROC-AUC", f"{d(m1['test']['roc_auc'])}, {d(m2['test']['roc_auc'])}, {d(m3va['test']['roc_auc'])}"),
    ("Model 3 test: accuracy / precision / recall / F1 / ROC-AUC",
     f"{d(m3['test']['accuracy'])} / {d(m3['test']['precision'])} / {d(m3['test']['recall'])} / {d(m3['test']['f1'])} / {d(m3['test']['roc_auc'])}"),
    ("Model 3 shuffled 5-fold CV (F1, ROC-AUC)", f"{d(m3['cv']['f1_mean'])} ± {d(m3['cv']['f1_sd'])}, {d(m3['cv']['auc_mean'])} ± {d(m3['cv']['auc_sd'])}"),
    ("Model 3 test ROC-AUC, 95% bootstrap CI", ci(m3)),
    ("Model 3 PR-AUC (random ranking)", f"{d(m3['test']['pr_auc'])} ({d(m3['test_prevalence'])}); CI {ci(m3, 'pr_auc')}"),
    ("Model 3 new-area ROC-AUC", d(m3["new_area_auc"])),
    ("Spring type only / climate only ROC-AUC", f"{d(typ['test']['roc_auc'])} / {d(clim['test']['roc_auc'])}"),
    ("Model 3b (drought-dried) ROC-AUC: test / new area", f"{d(m3b['test']['roc_auc'])} / {d(m3b['new_area_auc'])}"),
    ("Model 3b test ROC-AUC, 95% bootstrap CI", ci(m3b)),
    ("Model 3b PR-AUC (random ranking)", f"{d(m3b['test']['pr_auc'])} ({d(m3b['test_prevalence'])})"),
    ("Earthquake-dried vs active ROC-AUC (95% CI)", f"{d(eq['test']['roc_auc'])} ({ci(eq)})"),
    ("Test springs sharing coordinates with a training spring", f"{k['test_dup_coords']}; test ROC-AUC without them {d(k['test_auc_without_dups'])}"),
    ("Spring type share of impurity importance", f"{perennial_imp:.1f}%"),
    ("Distinct input combinations / lookup-table AUC", f"{k['n_distinct_rows']} / {d(k['lookup_table_auc'])}"),
    ("Drying causes: earthquake / drought", f"{f['drying_cause']['earthquake']} / {f['drying_cause']['drought']}"),
]

FIGURES = [
    ("Study area map", "Where the watershed is; springs were selected by spatial join to this boundary."),
    ("Drying year by cause", "The 2015 spike is mostly earthquake-attributed drying, which climate cannot explain."),
    ("Elevation, aspect, roads", "Descriptive patterns only (more drying at low elevation, on SW/S/W slopes, near roads); not causal and not predictors in Model 3."),
    ("Climate time series with windows", "Why Version A leaks: dried springs' windows end in different (mostly earlier) years than active springs' windows."),
    ("Climate distributions, Version A vs B", "Under A the classes separate strongly (artefact); under B the trend distributions almost overlap."),
    ("Confusion matrix + ROC (Model 3)", f"Read the four cells ({cm['tn']}, {cm['fp']}, {cm['fn']}, {cm['tp']}); the curve above the diagonal means better than chance."),
    ("Feature importance (Model 3)", "Spring type dominates both impurity and permutation importance."),
    ("Comparison chart", "Blue bars: random test and CV. Orange bars: new areas, always lower. Model 3b is the highest."),
]

QA = [
    ("Summarise your project in two minutes.",
     " ".join(SUMMARY[:2]) + " The first models looked perfect but were leaking the answer through the choice of years; "
     f"after the fix, the honest result is ROC-AUC {d(m3['test']['roc_auc'])}, and {d(m3b['test']['roc_auc'])} for drought-related drying."),
    ("Why did your accuracy drop from about 99% to about 72%?",
     f"The 99% models used Version A windows, where the years of climate data depended on whether the spring had dried. "
     f"The window end year alone predicts the label (ROC-AUC {d(k['leakage_diagnostic']['roc_auc'])}), so the models learned "
     f"the timing, not climate. With one common window the leakage disappears and the honest accuracy is {d(m3['test']['accuracy'])}. "
     f"The drop is a correction, not a failure."),
    ("How do you know it was leakage and not a genuinely strong climate signal?",
     f"Three pieces of evidence: (1) a model with no climate data at all, only the window end year, reaches ROC-AUC "
     f"{d(k['leakage_diagnostic']['roc_auc'])}; (2) the most important features in the leaky models were the trends, which are the "
     f"features most sensitive to the choice of years; (3) under the fixed window the trend distributions of active and dried "
     f"springs almost overlap (median precipitation trend {c['medians_version_b']['Precipitation_rate']['active']:.1f} vs "
     f"{c['medians_version_b']['Precipitation_rate']['dried']:.1f}), whereas under Version A they were "
     f"{c['medians_version_a']['Precipitation_rate']['active']:.1f} vs {c['medians_version_a']['Precipitation_rate']['dried']:.1f}."),
    ("Is an ROC-AUC of 0.75 good?",
     f"It is clearly better than chance (0.5) and moderate in strength. It is in the same range as related published "
     f"Random Forest results, for example 0.748 for water-spring potential in Jordan (Al-Shabeeb et al. 2023), and above the "
     f"0.60 prediction-rate AUC of groundwater mapping in Shivapuri, Nepal (Upadhyaya et al. 2024). These are different tasks, "
     f"so the comparison is only a plausibility check."),
    ("Your accuracy (0.719) is lower than just predicting 'active' for everything. Why?",
     f"Predicting 'active' for all test springs would give {all_active_acc:.3f} accuracy but would find zero dried springs. "
     f"With balanced class weights the model deliberately finds dried springs ({cm['tp']} of {cm['tp'] + cm['fn']}) at the cost of "
     f"some false alarms. That is why recall, F1 and ROC-AUC matter more than accuracy here."),
    ("Why Random Forest?",
     "It handles non-linear relationships and interactions, works with mixed features without heavy preprocessing, gives "
     "importance scores, and is a standard baseline in spring and groundwater studies. Comparing other algorithms is planned "
     f"for the dissertation; with only {k['n_distinct_rows']} distinct input combinations, other algorithms would currently give "
     "the same result."),
    ("Random Forest does not need VIF. Why did you use it?",
     f"Not for accuracy but for interpretation: highly correlated features split importance between them and transfer badly "
     f"to new areas (Dormann et al. 2013). Dewpoint mean had VIF {m3['vif']['dropped'][0][1]:.0f}, almost a copy of temperature. "
     f"VIF was fitted on training springs only, inside the pipeline, to avoid leakage."),
    ("Why class weights and not SMOTE?",
     "Class weighting is simpler and creates no synthetic springs. SMOTE is planned for the dissertation comparison and must be "
     "applied only inside training folds (Santos et al. 2018)."),
    ("Spring type is the strongest predictor. Isn't that trivial, or even leakage?",
     f"It is physically expected that seasonal springs dry more often ({f['pct_dried_seasonal']:.1f}% vs "
     f"{f['pct_dried_perennial']:.1f}%). But if surveyors recorded springs that had dried as 'seasonal', part of it could encode "
     f"the outcome. I list this as a limitation and the survey protocol should be checked."),
    ("Your springs are in only 12 grid cells. Does climate really add anything?",
     f"Within the watershed, yes: climate + spring type ({d(m3['test']['roc_auc'])}) beats spring type alone "
     f"({d(typ['test']['roc_auc'])}). But climate acts like a cell identifier: a lookup table gives the same AUC "
     f"({d(k['lookup_table_auc'])}), and in unseen cells climate alone falls to {d(clim['new_area_auc'])}. "
     f"So the honest answer is: the signal exists, but the data are too coarse to show climate effects between nearby springs."),
    ("What is Model 3b and isn't filtering the data cherry-picking?",
     f"Model 3b keeps only springs whose drying the survey attributes to drought ({f['drying_cause']['drought']}) and compares "
     f"them with all active springs. The cause comes from the survey, not from the model, and the proposal already plans label "
     f"screening (Section 7.3). I also report the contrast: earthquake-dried springs give only ROC-AUC {d(eq['test']['roc_auc'])}. "
     f"Climate explaining drought drying better than earthquake drying is what physics predicts."),
    ("Why is Model 3b's F1 lower if its AUC is higher?",
     f"Dried springs are only {100 * m3b['n_dried'] / m3b['n_rows']:.1f}% of Model 3b's data, so even a good ranking produces "
     f"more false alarms ({m3b['confusion']['fp']}) than true detections ({m3b['confusion']['tp']}). Precision and F1 depend on "
     f"prevalence; AUC does not. That is why models are compared with AUC."),
    ("Could your result just be a lucky train/test split?",
     f"I resampled the test springs 2,000 times (bootstrap). The 95% interval for Model 3's test ROC-AUC is {ci(m3)}, well above "
     f"0.5. Model 3b's interval ({ci(m3b)}) lies entirely above Model 3's and above the earthquake contrast's ({ci(eq)}), so the "
     f"drought result is not a chance difference. Cross-validation agrees ({d(m3['cv']['auc_mean'])} ± {d(m3['cv']['auc_sd'])}). "
     f"The interval covers which springs land in the test set, not the choice of grid cells; that is what the new-area test is for."),
    ("Your data are imbalanced. Why not report precision-recall?",
     f"I do. Model 3's PR-AUC is {d(m3['test']['pr_auc'])}; random ranking would give {d(m3['test_prevalence'])}, the share of dried "
     f"springs, so it is about {m3['test']['pr_auc'] / m3['test_prevalence']:.1f} times chance. Model 3b's PR-AUC "
     f"({d(m3b['test']['pr_auc'])}) looks lower, but its chance level is only {d(m3b['test_prevalence'])}, so it is "
     f"{m3b['test']['pr_auc'] / m3b['test_prevalence']:.1f} times chance. PR-AUC must always be read against its baseline."),
    ("You have duplicate springs. Don't they inflate the score?",
     f"I checked. {k['test_dup_coords']} test springs share coordinates with a training spring. Removing them gives a test "
     f"ROC-AUC of {d(k['test_auc_without_dups'])}, the same as {d(m3['test']['roc_auc'])} with them, so they do not inflate the result."),
    ("Why the window 2009 to 2023?",
     f"The survey was carried out mostly between {f['survey_dates']['p05']} and {f['survey_dates']['p95']}, and the latest drying "
     f"year is {f['drying_year']['max']}. Spring status therefore describes 2023, and 15 years ending in 2023 is 2009 to 2023."),
    ("Why ERA5-Land and not weather stations?",
     "Stations are sparse in the mid-hills and do not cover every spring. ERA5-Land gives continuous, consistent data since 1950 "
     "at about 9 km. Its weakness is resolution and mountain precipitation bias, which I discuss as a limitation."),
    ("Why Mann-Kendall and Sen's slope?",
     "They are the standard non-parametric trend methods in hydro-climate studies: no normality assumption, and Sen's slope is "
     "resistant to outlier years (Mann 1945; Sen 1968)."),
    ("Why exclude land cover, geology and roads?",
     "The proposal focuses on climate. Land cover cannot be projected under the SSP scenarios and is missing before 2000; "
     "geology is too coarse; roads are kept as descriptive context. Models 1 and 2 show them only for transparency."),
    ("Why did your cross-validation F1 change from 0.36 to 0.51?",
     f"The submitted version used folds in file order. The file is ordered, so the dried share per fold ranged from "
     f"{min(k['dried_pct_by_file_fifth']):.1f}% to {max(k['dried_pct_by_file_fifth']):.1f}%. Shuffled stratified folds give "
     f"{d(m3['cv']['f1_mean'])} ± {d(m3['cv']['f1_sd'])}, consistent with the test set."),
    ("Why did you not implement the data augmentation?",
     f"Checking it on the data showed three problems: the dried share only rises to {f['augmentation']['pct_dried_after']:.1f}%; "
     f"{f['augmentation']['dried_rows_before_2015']:,} dried rows fall in years with no active rows, so the year would leak the "
     f"label again; and rows after drying use climate from after the spring dried. A year-by-year survival-style design is better."),
    ("Can your model predict future drying under climate change?",
     "Not yet. A model that has mostly learned which grid cell a spring is in cannot respond meaningfully to future climate. "
     "Scenario projection needs spring-scale climate inputs and climate-related labels first; that is the dissertation plan."),
    ("What are the main limitations?",
     f"Coarse climate data ({f['grid']['n_cells']} cells); labels from a single community survey; about {eq_share:.0f}% of dried "
     f"springs attributed to the earthquake; spring type possibly encoding the outcome; random-split evaluation; one algorithm "
     f"without tuning."),
    ("What is your main contribution?",
     "A reproducible spring-level dataset and pipeline; detecting and proving a leakage problem that made results look perfect; "
     "an honest baseline; and showing, through label screening by cause and the new-area test, where the climate signal is and "
     "where it is not. These findings directly shape the dissertation design."),
    ("What will you do next?",
     "Screen labels by cause and persistence; build a year-by-year design using year-to-year climate variation; add finer "
     "climate inputs (elevation-adjusted temperature, better precipitation); compare algorithms (logistic regression, XGBoost, "
     "SVM); test transfer to Panchkhal, reporting springs in new cells separately; then SHAP and SSP scenarios."),
    ("Why do the numbers differ from your submitted report?",
     "Three bugs and inconsistencies were found and corrected: the window years in the code (2011 to 2025) did not match the text "
     "(2009 to 2023), the cross-validation was unshuffled, and Model 1 cast features to integers. Appendix B lists every change. "
     "Reporting corrected numbers is part of doing the analysis properly."),
]

TIPS = [
    "Lead with the leakage story: it shows critical thinking and is the strongest part of the project.",
    "Always say which score you mean: test set, cross-validation or new area.",
    "Use ROC-AUC to compare models; explain accuracy and F1 only with the class imbalance in mind.",
    "When asked about causes, say 'associated with', not 'caused by'. The models do not establish causality.",
    "Admit limitations directly and follow with the planned fix. Examiners value this more than a high score.",
    "Keep the cheat-sheet numbers in front of you; every number in it matches the report exactly.",
]


# ------------------------------------------------------------------ document
def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd"); s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), color)
    tcPr.append(s)


def table(doc, header, rows, widths=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(header)); t.style = "Table Grid"
    for j, h in enumerate(header):
        cell = t.cell(0, j); cell.text = ""; r = cell.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(10)
        shade(cell, "D9E2F3")
    for i, row in enumerate(rows, 1):
        for j, v in enumerate(row):
            cell = t.cell(i, j); cell.text = ""; r = cell.paragraphs[0].add_run(v); r.font.size = Pt(10)
            if j == 0:
                r.bold = True
    doc.add_paragraph()


def main():
    doc = Document()
    st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
    st.paragraph_format.space_after = Pt(4)
    for name in ("Heading 1", "Heading 2", "Heading 3"):
        doc.styles[name].font.color.rgb = RGBColor(0x1F, 0x3B, 0x5C)

    t = doc.add_heading("Spring Drying Project: A to Z Study and Defence Guide", 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph("Roshi Khola watershed | Random Forest | ERA5-Land climate | All numbers match the revised report")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_heading("1. The project in one page", 1)
    for s in SUMMARY:
        doc.add_paragraph(s, style="List Bullet")

    doc.add_heading("2. Key numbers cheat sheet", 1)
    table(doc, ["Item", "Value"], NUMBERS)

    doc.add_heading("3. A to Z glossary", 1)
    doc.add_paragraph("Each entry gives the meaning in plain words and what it means in this project.")
    for letter, entries in GLOSSARY.items():
        doc.add_heading(letter, 2)
        for term, meaning, here in entries:
            p = doc.add_paragraph()
            r = p.add_run(term + ": "); r.bold = True
            p.add_run(meaning)
            p2 = doc.add_paragraph()
            p2.paragraph_format.left_indent = Pt(18)
            r = p2.add_run("In this project: "); r.italic = True; r.bold = True
            p2.add_run(here.replace("`", ""))

    doc.add_heading("4. Figures you should be able to explain", 1)
    table(doc, ["Figure", "What to say"], FIGURES)

    doc.add_heading("5. Likely examiner questions and answers", 1)
    for i, (q, a) in enumerate(QA, 1):
        p = doc.add_paragraph(); r = p.add_run(f"Q{i}. {q}"); r.bold = True
        doc.add_paragraph(a).paragraph_format.left_indent = Pt(18)

    doc.add_heading("6. Tips for the defence", 1)
    for s in TIPS:
        doc.add_paragraph(s, style="List Bullet")

    out = ROOT / "report" / "Defense_Guide_AZ.docx"
    doc.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
