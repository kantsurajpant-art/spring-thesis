# 9-credit project report: consistency check against the code

> **Status (2026-10-06): all items below are resolved in the revised report in `report/`.** Appendix B of that report lists
> every correction. The numbers in this file came from an earlier run. The authoritative values are now in `report/numbers.json`.
> They are identical for Model 3; Version A models were re-run with the corrected 2009–2023 window.

*Report: "Dataset Preparation and ML-Based Classification of Spring Status" (26 Sep 2026).
Checked against the notebooks and data on 2026-10-04.*

The report's central story holds: Version A leaked the label, Model 3 fixed it, and Model 3 gives F1 0.476 and ROC-AUC 0.748.
The items below are places where the text does not match what the code did.

## Final numbers to use (from `notebooks/model3_final.ipynb`)

Window 2009–2023, VIF on training springs only, shuffled 5-fold CV. Same RF settings as the report.

**Model 3 (§6.3 / §7.4)**
- Test set (n = 987): Accuracy 0.719, Precision 0.405, Recall 0.578, F1 0.476, ROC-AUC 0.748
- Confusion matrix: 584/769 active correct, 185 active called dried, 126/218 dried correct, 92 dried missed
- 5-fold CV (shuffled): F1 **0.511 ± 0.023**, ROC-AUC 0.760 ± 0.011 *(replaces 0.360 ± 0.106, which came from unshuffled folds)*
- VIF dropped: Dewpoint_mean (936.0), then Evaporation_mean (75.6). Kept: Dewpoint_rate, Temperature_rate, Precipitation_rate,
  Evaporation_rate, Temperature_mean, Precipitation_mean + Perennial/Seasonal
- Importance: Perennial/Seasonal 64.9 %, Precipitation_rate 8.6 %, Temperature_mean 7.4 %, Temperature_rate 6.6 %,
  Precipitation_mean 5.0 %, Dewpoint_rate 3.9 %, Evaporation_rate 3.6 %. Permutation importance confirms that spring type
  carries almost all of the test-set signal (AUC drop 0.164; each climate variable ≤ 0.003).
- Version A leakage check (window end year alone): AUC 0.986, F1 0.986

**Comparison table (new section)**

| Configuration | Springs (dried) | Test AUC | CV AUC | CV F1 | New-area AUC |
|---|---|---|---|---|---|
| Spring type only | 3,287 (727) | 0.651 | 0.662 | 0.480 | 0.584 |
| Climate only | 3,287 (727) | 0.625 | 0.637 | 0.401 | 0.527 |
| **Model 3** (climate + type) | 3,287 (727) | **0.748** | **0.760** | **0.511** | **0.630** |
| **Model 3b**: drought-dried vs active | 2,786 (226) | **0.854** | **0.862** | 0.391 | **0.752** |
| Model 3b: drought-dried, climate only | 2,786 (226) | 0.771 | 0.768 | 0.292 | 0.543 |
| Contrast: earthquake-dried vs active | 2,789 (229) | 0.709 | 0.704 | 0.214 | 0.571 |

Drying causes of the 727 dried Roshi springs (raw survey "Reason of drying"): earthquake 229 (195 of them dried in 2015),
drought / reduced precipitation 226, infrastructure 105, neglect or disruption 95, natural disaster 64, land use 5, unknown 3.

F1 is lower for Model 3b because dried springs are rarer there (8 % instead of 22 %). Compare models with ROC-AUC.

## Must fix (factual mismatches)

| # | Report says | Code / data actually | Fix |
|---|---|---|---|
| 1 | Version A active and Version B windows are **2009–2023** (§4.8.3, §6.3, §6.4, Fig 7, §9) | Both used **2011–2025** (`WINDOW_END = 2025`; Version A CSV values match 2011–2025 exactly) | Keep 2009–2023, the survey year, and update the numbers in rows 2–4 from the re-run. Or change the text to 2011–2025. |
| 2 | §6.3 VIF: drops Dewpoint_mean (215.07), then Evaporation_rate (33.58); keeps Evaporation_mean | With 2009–2023: drops Dewpoint_mean (922.49), then **Evaporation_mean** (76.04); keeps **Evaporation_rate** | Update §6.3 |
| 3 | §6.3/§7.4 metrics | Re-run with 2009–2023: Acc 0.7194, P 0.4051, R 0.5780, F1 0.4764, **AUC 0.7483**, CV F1 0.360 ± 0.106 | Only the AUC moves (0.748 either way) |
| 4 | §7.4/§9 importances: perennial 65.3 %, precip trend 10.0 %, temp mean 8.2 %, precip mean 5.8 % | 2009–2023: perennial 64.9 %, precip trend 8.5 %, temp mean 7.3 %, temp trend 6.8 %, precip mean 5.0 % | Update the numbers |
| 5 | §6.4/§9: window end year alone gives "perfect" classification | 2011–2025: AUC 1.0. 2009–2023: AUC 0.986 (springs dried in 2023 share the end year) | Say "near-perfect (AUC 0.99)" |
| 6 | §4.8 + Table 1: ERA5, 0.25° (~27 km), hourly | File is **ERA5-Land, 0.1° (~9–11 km), monthly** (916 monthly steps, 1950-01 to 2026-04). Abstract, §1.3 and §9 already say ERA5-Land. | Make §4.8 and Table 1 match |
| 7 | §6.4: "Model 2's ROC-AUC exactly 1.0 and F1 0.99" | Those numbers come from `random_forest_proposal_compliant_model.ipynb` (Version A, climate and perennial only). Model 2 as described in §6.2 has no notebook in the folder. | Attribute the numbers to the right model, or add it as a model |
| 8 | Fig 10 (Model 2 confusion matrix) | Identical to Fig 8 (Model 1): 767 / 1 / 2 / 216 | Check that it isn't a copied figure. The Model 2 code is not in the project folder. |

## Should fix (reasoning built on a code bug)

9. **Model 1 casts all features to `int`** (`X = ...astype(int)`). Dewpoint_rate, Temperature_rate, Evaporation_rate, Evaporation_mean and Slope_cos all become 0. That is why
   they are missing from Fig 9. §6.2 then removes evaporation because "Model 1 showed it contributed little". That justification is an artefact of the bug.
   Use the VIF or proposal-scope reasoning instead.
10. **The slope features are broken.** `Slope_sin` is ≈ 1.0 and `Slope_cos` is ≈ 0 for every spring, which means a slope of about 90° everywhere (most likely computed on a degree-based DEM).
    §4.4 also says sin/cos avoids a "0°/360° wrap-around", which applies to *aspect*, not slope (slope runs 0–90°). Slope is only used in Models 1 and 2.
11. §4.10: the code's cutoff is 1946, but ERA5-Land starts in 1950. The 3 springs that dried 1946–1964 got windows shorter than 15 years, so they are not "complete".
    Also, 4 springs labelled dried have no drying year, so Version A gave them the active window.

## Worth adding as a limitation (one paragraph in §7.5)

12. **All 3,287 springs fall into only 12 ERA5-Land grid cells**, so the climate features take just 12 distinct values. The 70/30 random split puts
    springs from the same cell in both train and test. Leave-one-grid-cell-out CV gives ROC-AUC **0.60** (climate alone 0.54),
    against 0.75 with the random split. Run `python scripts/spatial_cv_check.py`. The proposal (§10) already names ERA5-Land resolution as a limitation,
    so this just quantifies it. Expect it as a viva question.
13. Perennial/seasonal carries 65 % of importance. Say whether surveyors could have recorded springs that had since dried as "seasonal", which would make this feature partly encode the label.

## §6.5 / §8.1 augmentation: problems to note before the dissertation

Checked against the actual drying years (rows: active 2015–2023, dried Y–2023, Y ≥ 1964):

- **Class balance barely changes.** You get 23,040 active rows and 8,795 dried rows, so the dried share goes from 22.1 % to only 27.6 %.
- **It brings the leakage back.** 3,021 dried rows (34 %) fall in years before 2015, where no active rows exist, so the row's year predicts the label again.
  Only generate rows for years in which both classes are present.
- **Post-drying climate.** A spring that dried in 2010, given a 2020 row, is described by 2006–2020 climate, mostly *after* it dried. That cannot explain drying.
- **The independence problem is larger than §6.5 states.** In any given year every spring in a grid cell has identical climate, so the extra rows add no
  between-spring information. CV must group by **grid cell**, not just by spring.
