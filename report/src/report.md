%% Source of the project report. Build with:  python scripts/build_report.py
%% Every number in {{...}} is filled from report/numbers.json (written by scripts/export_report_numbers.py
%% from the notebook outputs). Do not type statistics by hand. Only verified references may be cited.

# Acknowledgements {-}

I would like to express my sincere gratitude to my project supervisor, Prof. Santosh Khanal, for his valuable guidance, support, and constructive feedback throughout the course of this project.

I would also like to acknowledge the Springshed Management team at the International Centre for Integrated Mountain Development (ICIMOD) for providing access to the community-based spring inventory data used in this study. Their efforts in generating and documenting field-based spring information provided an important foundation for this research.

# Abstract {-}

Springs are important sources of domestic and agricultural water in the mid-hills of Nepal, but many are becoming less reliable, and some have already dried. This project examined whether the status of springs in the Roshi Khola watershed can be classified from climate variables and a basic spring characteristic using machine learning. A community-based inventory of {{facts.n_springs:,}} springs ({{facts.n_dried}} dried, {{facts.n_active:,}} active) was combined with ERA5-Land reanalysis climate data to prepare a spring-level analysis dataset, while topographic, land-cover, geological and road-network information was prepared for contextual analysis. Random Forest models were developed to classify springs as active or dried using 15-year climate means and trends together with the perennial/seasonal spring classification.

During model development, a temporal leakage problem was identified. When the climate window of each dried spring ended at its own reported drying year and that of each active spring at the survey year, the end year of the window alone separated the two classes almost perfectly (ROC-AUC {{checks.leakage_diagnostic.roc_auc:.3f}}), and models built on these features reached ROC-AUC values of {{min(m1.test.roc_auc, m2.test.roc_auc, m3va.test.roc_auc):.3f}} to {{max(m1.test.roc_auc, m2.test.roc_auc, m3va.test.roc_auc):.3f}}. The design was corrected by applying one common 15-year window ({{climate.window.replace("-", " to ")}}) to every spring. With multicollinearity screening fitted on the training data, the final model (Model 3) achieved accuracy {{m3.test.accuracy:.3f}}, precision {{m3.test.precision:.3f}}, recall {{m3.test.recall:.3f}}, F1-score {{m3.test.f1:.3f}} and ROC-AUC {{m3.test.roc_auc:.3f}} (95% bootstrap CI {{m3.test_ci.roc_auc[0]:.3f}} to {{m3.test_ci.roc_auc[1]:.3f}}) on a held-out test set, with a shuffled 5-fold cross-validated F1 of {{m3.cv.f1_mean:.3f}} ± {{m3.cv.f1_sd:.3f}}. When springs whose drying was attributed to the 2015 earthquake or other non-climatic causes were excluded and only drought-dried springs were compared with active springs (Model 3b), ROC-AUC rose to {{m3b.test.roc_auc:.3f}}. However, all {{facts.n_springs:,}} springs fall within only {{facts.grid.n_cells}} ERA5-Land grid cells, and when whole cells were held out the ROC-AUC of Model 3 fell to {{m3.new_area_auc:.3f}}. The selected climate variables and the perennial/seasonal classification therefore carry moderate within-watershed predictive information, much of it tied to location and spring type. The project provides a defensible, reproducible baseline for the dissertation work on improved climate inputs, model comparison, spatial transferability and future climate scenarios.

**Keywords:** spring drying; machine learning; Random Forest; data leakage; ERA5-Land; Roshi Khola watershed

<<TOC>>

# Abbreviations {-}

Table: Abbreviations {-}
| Abbreviation | Meaning |
|---|---|
| AD | Anno Domini (Gregorian calendar year) |
| AUC | Area under the (ROC) curve |
| BS | Bikram Sambat (Nepali calendar) |
| CV | Cross-validation |
| DEM | Digital elevation model |
| ERA5 / ERA5-Land | Fifth-generation ECMWF reanalysis / its land-surface component |
| ICIMOD | International Centre for Integrated Mountain Development |
| HKH | Hindu Kush Himalaya |
| LULC | Land use and land cover |
| ML | Machine learning |
| RF | Random Forest |
| ROC | Receiver operating characteristic |
| SHAP | SHapley Additive exPlanations |
| SMOTE | Synthetic Minority Over-sampling Technique |
| SRTM | Shuttle Radar Topography Mission |
| SSP | Shared Socioeconomic Pathway |
| VIF | Variance inflation factor |

<<MAINMATTER>>

# Introduction {#sec:intro}

## Background {#sec:background}

Springs are a major source of water for communities in the Hindu Kush Himalaya, particularly in the mid-hills where settlements are scattered and piped water systems do not always provide a reliable supply. They support drinking water, livestock, small-scale irrigation and local ecosystems [@icimod2009; @tambe2012; @agrawal2023]. A spring is not simply a point where water appears at the surface. Its condition depends on the recharge area, the subsurface pathways and the wider landscape through which water moves before emerging [@chinnasamy2016].

At the Himalayan scale, groundwater is not a minor residual component of the water cycle. @andermann2012 showed from multi-decadal precipitation and discharge records in Nepal that transient groundwater storage in fractured basement aquifers contributes substantially to river discharge. Springs are therefore better treated as expressions of catchment and aquifer storage than as isolated surface-water points.

Large inventories document the scale of spring decline. @adhikari2021 mapped more than 4,222 springs across five watersheds in western Nepal and estimated that the discharge of about 70% of them was decreasing, while @pandit2024 found a continuous declining trend in flow in 73% of 1,122 springs in the Rangun Khola watershed, with 2% already dried. A synthesis of spring research in Nepal reported that about 16% of springs had already dried and about 60% had declining discharge [@chauhan2023]. In Kavrepalanchowk District, the community-based inventory used in this project documented 5,689 water sources, of which 27% had dried [@pandit2026]. Declining springs affect household water security, increase the burden of collecting water and reduce the water available for agriculture and livestock. Decline on this scale justifies moving from descriptive inventories towards reproducible analytical and predictive approaches.

Spring decline rarely has a single cause. Changes in land use, road construction, slope disturbance, geology and groundwater pathways can all influence recharge. Climate matters as well, since temperature, rainfall amount and timing, atmospheric moisture and evaporative demand determine how much water is available for infiltration and recharge [@sharma2019; @forsythe2021; @nepal2021]. In a monsoon-dominated mountain environment, even small changes in rainfall distribution or dry-season conditions may affect spring persistence.

## Problem statement {#sec:problem}

Although spring inventories are becoming more common in Nepal, they are still used mainly to describe the present condition of water sources. There is limited work linking these point-based inventories with long-term climate information to test whether the status of an individual spring can be predicted. Physically based groundwater models would be valuable for this purpose, but they require detailed hydrogeological parameters and long discharge records that are not available for most springs in the mid-hills [@poudel2017].

Machine learning offers a practical way to explore the problem when the available information is incomplete but the number of observations is relatively large. @granata2018, for example, showed that Random Forest and other data-driven algorithms can forecast spring discharge when appropriate climatic and hydrological inputs are available. Here, machine learning is not a replacement for hydrogeological understanding; it is a way to test whether incomplete, multi-source data contain a reproducible predictive signal. Machine-learning results can also be misleading when information linked to the outcome enters the predictors, a problem known as target leakage [@kaufman2011; @kapoor2023]. The present project therefore treats the checking of leakage and of the validation design as part of the analysis, rather than focusing only on a high accuracy score.

## Rationale and scope of the project {#sec:scope}

This report is the first phase of a larger dissertation on spring drying under climate change. Its scope is intentionally narrower: it develops and evaluates a Random Forest classifier for active and dried springs within the Roshi Khola watershed. The final model uses climate summaries derived from ERA5-Land together with the perennial/seasonal spring classification. Other prepared datasets, including topography, land cover, geology and roads, are retained for interpretation and later analysis but are not part of the proposal-compliant predictor set in this phase.

The dissertation is expected to compare additional algorithms, test whether a model trained in Roshi can be transferred to other mid-hill areas, and examine future drying risk under climate-change scenarios. These later tasks are not presented as completed work here. All analyses in the report can be reproduced from the project repository (Appendix A), and corrections made relative to the version submitted on 26 September 2026 are listed in Appendix B.

# Literature Review {#sec:lit}

## Spring drying in the Himalayan mid-hills {#sec:lit-drying}

Springs have long been described as lifeline water sources in Himalayan hill communities because they provide water close to settlements and often function without large infrastructure [@icimod2009; @tambe2012]. Their reliability, however, depends on recharge and groundwater storage. When recharge declines or subsurface flow paths are disturbed, discharge can fall gradually, become seasonal, or stop altogether. In the Thulokhola watershed of Nuwakot, 73.2% of surveyed springs had decreased flow and 12.2% had dried over the preceding decade or more [@poudel2017], and similar declines have been reported elsewhere in Nepal [@adhikari2021; @pandit2024].

Climate can affect springs through several linked processes. Higher temperature raises evaporative demand, while changes in monsoon timing and rainfall intensity influence infiltration and soil-water storage. Heavy rainfall does not necessarily mean greater recharge, because intense events may produce rapid runoff, especially on steep or disturbed slopes [@sharma2019; @forsythe2021]. In the Sikkim Himalaya, @tambe2012 linked the problem of dying springs to a rise in rainfall intensity, a reduction in its temporal spread and a decline in winter rain, and reported that lean-period discharge was perceived to have declined by nearly 50% in drought-prone areas over a decade. @pandit2024 found a significant increase in temperature and in the frequency of localised high-intensity rainfall concurrent with declining spring flow, alongside land-cover change and road expansion. For these reasons it is useful to consider both the long-term mean climate and the direction of change, rather than a single annual value.

## Non-climatic causes of drying {#sec:lit-nonclimate}

Drying is not only climatic. In the Melamchi area of the Middle Hills, the 2015 Nepal earthquake had an immediate drying effect on about 18% of the surveyed springs, while the water volume of about 30% of springs had decreased over the previous decade [@chapagain2019]. A survey of leaders of 300 local government units across Nepal found that springs had dried in 74% of units and that road and infrastructure construction was perceived as the main cause, followed by earthquakes and climate change [@thapa2023]. The Kavre inventory itself attributes drying to earthquakes, droughts and infrastructure development [@pandit2026]. A climate-only model can therefore explain only part of the drying recorded in an inventory, which is why this report introduces label screening by reported cause ([[sec:m3b]]).

## Environmental controls beyond climate {#sec:lit-controls}

Spring occurrence and persistence are also controlled by physical setting. Elevation, slope and aspect affect runoff, solar exposure and local moisture conditions [@broxton2009; @gutierrez2013]; topography and geology control groundwater flow in mountainous terrain [@forster1988; @condon2015]; bedrock structure and lineaments influence where springs emerge [@doctor2008; @ra2018]; and land-cover change can alter infiltration and evapotranspiration [@jayawickreme2007; @bosmans2017; @pant2026]. Roads and other infrastructure may intercept shallow groundwater or redirect surface and subsurface flow [@montgomery1994; @dutton2005].

@chinnasamy2016 argue that spring investigations should combine information on climate, land use, geology, hydrology and groundwater pathways, because no single layer adequately represents the recharge-to-discharge process. The supporting dataset prepared in this project follows that logic: DEM-derived terrain variables represent gravitational and moisture controls; lithology represents storage and permeability contrasts; land cover represents infiltration and evapotranspiration conditions; and roads provide a proxy for anthropogenic disturbance. These layers are left out of the final predictor set as a scope decision of the proposal, not because they are assumed to be unimportant.

## Machine learning and groundwater-related prediction {#sec:lit-ml}

Machine-learning methods are increasingly used in hydrology where spatial datasets are large but the processes are too complex or poorly observed for a detailed physical model. Random Forest [@breiman2001] is common because it handles non-linear relationships and interactions and is relatively insensitive to the scale of the variables. Most spring-related machine-learning studies, however, predict where springs or groundwater are likely to occur rather than whether a mapped spring is active or dried. In the Central Himalaya, @niraula2021 trained Random Forest variants on 621 spring and 815 non-spring locations and reported 92% accuracy for a Bootstrap Forest, falling to 75% on an independent dataset. @pradhan2025 compared logistic regression and Random Forest for groundwater potential zones in the hills of central Nepal, and @alfugara2020 compared machine-learning models for groundwater spring potential. For water-spring potential in Jordan, @alshabeeb2023 reported a test ROC-AUC of 0.748 for Random Forest, ahead of SVM (0.732), MARS (0.727) and boosted regression trees (0.689). @guo2023 showed that adding precipitation, evaporation and ground-surface temperature raised the AUC of a Random Forest groundwater-potential model by 0.073 (to 0.757 without climate factors for the baseline Random Forest).

For Nepal, @upadhyaya2024 mapped groundwater potential in Shivapuri Rural Municipality with frequency-ratio methods. Their modified method reached a success-rate AUC of 0.80 and the conventional method 0.65, while both methods had a prediction-rate AUC of 0.60. The success rate is computed on the data used to build the map and the prediction rate on held-out data, so it is the prediction-rate value that corresponds to the held-out test AUC reported in this project.

The closest published analogue to this project is @ishikawa2025, who classified 228 mapped springs in the Hangai Mountains of Mongolia as still discharging (192) or depleted (44) using logistic regression, Random Forest and SVM with vegetation indices and terrain-derived predictors. They reported ROC-AUC values of 0.84 to 0.86 and, because of the class imbalance, also precision-recall AUC. That study differs from the present one in its predictors (satellite indices rather than climate trends), sample size and setting. Spring-discharge forecasting is a further, distinct task that relies on continuous discharge records at a few monitored springs [@granata2018].

## Research gap {#sec:gap}

The literature shows a gap between descriptive spring inventories and predictive analysis. Spring decline is well recognised, and groundwater-potential mapping has been carried out in Nepal, but to the best of our knowledge (searches up to September 2026) no published study classifies the active or dried status of a large community spring inventory in Nepal from long-term reanalysis climate trends. There is also limited evidence on how such a model performs outside the area used for training. The present project addresses the first part of that gap within the Roshi Khola watershed; the dissertation phase will address model comparison, spatial transferability and scenario-based risk.

## Methodological implications {#sec:lit-methods}

Several lessons from the literature shape the design. First, leakage occurs when predictors contain information that would not legitimately be available at prediction time, and it is common across fields that use machine learning: @kapoor2023 found leakage in 17 fields affecting 294 papers. Climate windows defined from a reported drying year can encode the target in exactly this way ([[sec:leakage]]). Second, environmental observations are spatially and temporally structured, so random partitions can overstate predictive transfer. Cross-validation should respect such dependence [@roberts2017]; random cross-validation has been shown to overestimate AUC by up to 0.16 relative to spatially blocked designs [@koldasbayeva2025]; and transferability needs its own assessment, because good in-sample performance does not guarantee performance elsewhere [@wenger2012]. Third, correlated predictors require screening or careful interpretation [@dormann2013], and impurity-based Random Forest importance can be biased [@strobl2007]. Fourth, imbalanced outcomes require metrics that reflect minority-class performance rather than accuracy alone [@he2009; @saito2015]. Fifth, resampling such as SMOTE [@chawla2002] must be applied only inside training folds [@santos2018], and repeated observations from the same unit must be kept in the same fold [@john2025].

## Climate reanalysis in mountain terrain {#sec:lit-reanalysis}

ERA5 [@hersbach2020] and its land-surface counterpart ERA5-Land, which has a horizontal resolution of about 9 km [@munozsabater2021], provide spatially continuous climate fields where station networks are sparse. Evaluations in high-mountain Nepal show that air temperature is the best-captured variable, but that local- to micro-scale processes are not reproduced and monsoon precipitation is strongly overestimated [@khadka2022]. A global evaluation also found a general wet bias in ERA5 precipitation [@lavers2022]. Reanalysis values at spring locations should therefore be read as regional climate forcing rather than spring-scale microclimate.

# Research Questions and Objectives {#sec:rq}

## Research question for this report

The project is guided by one research question: can a machine-learning model trained on climate variables and a spring-intrinsic characteristic within the Roshi Khola watershed distinguish between active and dried springs with useful predictive skill?

The question is deliberately limited to within-watershed classification. Testing transferability to other municipalities and projecting future climate-related drying risk are part of the subsequent dissertation phase.

## Working hypothesis

The working hypothesis is that climate variables, together with the perennial/seasonal classification of a spring, contain measurable information related to whether the spring is active or dried. The model is therefore expected to perform better than random classification, although the strength and stability of that performance must be established from independent test data and cross-validation rather than assumed in advance.

## Objectives

The main objective is to develop and evaluate a Random Forest model for classifying spring status in the Roshi Khola watershed using climate variables and the perennial/seasonal spring attribute. The specific objectives are to:

- prepare a spring-level analysis dataset by linking the community spring inventory with the required spatial and climate information;
- derive 15-year climate means and trends for temperature, precipitation, dewpoint and potential evaporation;
- train and evaluate a Random Forest classifier while accounting for class imbalance and multicollinearity;
- check whether model performance is affected by the way climate windows are constructed, and correct the design if leakage is identified;
- test how sensitive the result is to the reported cause of drying and to evaluation in unseen areas; and
- establish a defensible, reproducible baseline for the dissertation work on algorithm comparison, spatial generalisability and future climate scenarios.

## Structure of the report

[[sec:data]] describes the study area and the datasets. [[sec:method]] presents the modelling method. [[sec:results]] documents the sequence of models, the temporal leakage and the final results. [[sec:discussion]] discusses the findings and their limitations, followed by future work and conclusions.

# Study Area and Data Sources {#sec:data}

## Study area {#sec:area}

A community-based spring inventory covering seven municipalities of Kavrepalanchowk District (Dhulikhel, Panchkhal, Roshi Rural Municipality, Panauti, Temal, Namobuddha and Bethanchowk) was prepared through ICIMOD's springshed management initiative [@pandit2026; @thapa2025]. The Roshi Khola watershed, which intersects these municipalities and lies in the mid-hills of central Nepal, was selected as the study area ([[fig:map]]).

![Roshi Khola watershed boundary and location within Nepal (inset).](study_area_map.jpg){#fig:map width=0.95}

Springs were assigned to the Roshi watershed using a spatial join against the watershed boundary polygon, since this boundary cuts across municipal administrative limits. [[tab:inventory]] summarises the inventory. The published description of the inventory reports 5,689 water sources, including 5,168 springs and 521 ponds [@pandit2026]; the survey export used in this project contains {{facts.raw.n_records:,}} records ({{facts.raw.n_springs:,}} springs and {{facts.raw.n_ponds}} ponds). After spatial filtering to the Roshi watershed and data-quality screening, {{facts.n_springs:,}} springs were retained as the analysis dataset. The other {{facts.outside.n_springs:,}} springs of the inventory are not used anywhere in this report and are reserved for the staged generalisability testing of the dissertation phase.

Table: Spring inventory and analysis dataset {#tab:inventory cols=LR}
| Item | Count |
|---|---|
| Records in the survey export (springs and ponds) | {{facts.raw.n_records:,}} |
| Spring records | {{facts.raw.n_springs:,}} |
| Pond records (not analysed) | {{facts.raw.n_ponds}} |
| Springs in the Roshi Khola analysis dataset | {{facts.n_springs:,}} |
| Active / dried springs in the analysis dataset | {{facts.n_active:,}} / {{facts.n_dried}} |
| Springs outside the analysis dataset (reserved) | {{facts.outside.n_springs:,}} |

## Spring inventory {#sec:inventory}

The inventory was collected by trained community resource persons with a mobile survey application, and the dataset is publicly available through ICIMOD's Regional Database System [@thapa2025]. It records the location and condition of each spring (active or dried) and, for dried springs, the year of drying. Most records are dated between {{facts.survey_dates.p05}} and {{facts.survey_dates.p95}} (5th to 95th percentile of the record dates; {{facts.survey_dates.pct_2024:.0f}}% of dated records are from 2024), so spring status describes conditions at the end of 2023 and in early 2024.

The raw survey records the drying year in the Bikram Sambat calendar. In the analysis table it was converted to the Gregorian (AD) calendar and stored in a column named *Dried since how many years?*, which in fact holds the calendar year of drying. For {{facts.bs_to_ad_offset["57"]}} of the {{facts.drying_year.n_with_year}} dried springs with a recorded year, the difference between the two calendars is exactly 57 years; the remaining entries are inconsistent and are treated as data-entry errors. Drying years range from {{facts.drying_year.min}} to {{facts.drying_year.max}} (median {{facts.drying_year.median:.0f}}); {{facts.drying_year.n_missing}} dried springs have no recorded year, and {{facts.drying_year.n_2015}} ({{facts.drying_year.pct_2015:.1f}}%) report 2015.

Of the {{facts.n_springs:,}} springs, {{facts.n_active:,}} ({{100 - facts.pct_dried:.1f}}%) are active and {{facts.n_dried}} ({{facts.pct_dried:.1f}}%) are dried; {{facts.n_perennial:,}} ({{facts.pct_perennial:.1f}}%) are classified as perennial and {{facts.n_seasonal}} ({{100 - facts.pct_perennial:.1f}}%) as seasonal. The perennial/seasonal classification is informative but not deterministic: {{facts.pct_dried_perennial:.1f}}% of perennial springs are dried, compared with {{facts.pct_dried_seasonal:.1f}}% of seasonal springs.

**Reported cause of drying.** The raw survey also records a *Reason of drying* for each dried spring. Matching the dried springs of the analysis dataset to the survey by coordinates gave a cause for all {{facts.n_dried}} of them ([[tab:cause]]). Earthquake and drought are reported almost equally often, and {{facts.earthquake_dried_in_2015}} of the {{facts.drying_cause.earthquake}} earthquake-attributed springs dried in 2015, the year of the Gorkha earthquake, which accounts for the spike of drying in that year ([[fig:cause]]).

Table: Reported cause of drying for the dried springs of the analysis dataset (Drought includes *Reduced Precipitation*) {#tab:cause cols=LRR}
| Reported cause | Dried springs | Share of dried (%) |
|---|---|---|
| Earthquake | {{facts.drying_cause.earthquake}} | {{100*facts.drying_cause.earthquake/facts.n_dried:.1f}} |
| Drought | {{facts.drying_cause.drought}} | {{100*facts.drying_cause.drought/facts.n_dried:.1f}} |
| Infrastructure development | {{facts.drying_cause.infrastructure}} | {{100*facts.drying_cause.infrastructure/facts.n_dried:.1f}} |
| Source neglected or disrupted | {{facts.drying_cause.neglect_or_disruption}} | {{100*facts.drying_cause.neglect_or_disruption/facts.n_dried:.1f}} |
| Natural disaster | {{facts.drying_cause.natural_disaster}} | {{100*facts.drying_cause.natural_disaster/facts.n_dried:.1f}} |
| Land use (deforestation, plantation) | {{facts.drying_cause.land_use}} | {{100*facts.drying_cause.land_use/facts.n_dried:.1f}} |
| Unknown | {{facts.drying_cause.unknown}} | {{100*facts.drying_cause.unknown/facts.n_dried:.1f}} |

![Dried springs by reported drying year (2000 to 2023) and reported cause.](overview_drying_year_by_cause.png){#fig:cause width=0.95}

## Watershed boundary and spatial harmonisation

A watershed boundary polygon was used to constrain all analysis to the target basin. Spring occurrence and behaviour are governed by catchment-scale hydrological processes; springs outside the basin are subject to different recharge regimes, and including them would introduce spatial heterogeneity unrelated to the study objective. All vector and raster datasets were projected into a common coordinate reference system before any overlay or extraction, because projection mismatches can shift point locations relative to raster cells or polygons and produce incorrect attribute assignments [@zandbergen2009].

Two data-quality observations bear on the evaluation. {{facts.quality.duplicate_coordinates}} springs share exact coordinates with another spring, and {{facts.quality.identical_rows}} rows are identical on all attributes; such duplicates can fall on both sides of a random train/test split. In the Model 3 split, {{checks.test_dup_coords}} test springs ({{checks.test_dup_coords_dried}} of them dried) share coordinates with a training spring, and leaving them out leaves the test ROC-AUC unchanged ({{checks.test_auc_without_dups:.3f}} against {{m3.test.roc_auc:.3f}}), so the duplicates do not inflate the reported performance.

## Topographic data (SRTM DEM) {#sec:topo}

Topographic information was derived from the SRTM digital elevation model [@farr2000; @yang2011]. Topography is one of the most important controls on groundwater emergence in mountainous terrain [@forster1988; @condon2015; @broxton2009]: elevation influences recharge zones and vertical climatic gradients; slope affects infiltration opportunity and runoff; and aspect controls solar exposure, evapotranspiration demand and local moisture conditions [@gutierrez2013]. Elevation was extracted at each spring's coordinates, and slope (S) and aspect (A) were derived from the elevation surface:

$$ S = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right) $$ || S = arctan( √( (∂z/∂x)² + (∂z/∂y)² ) )

$$ A = \arctan\left(\frac{\partial z/\partial y}{\partial z/\partial x}\right) $$ || A = arctan( (∂z/∂y) / (∂z/∂x) )

where ∂z/∂x and ∂z/∂y are the rates of change of elevation in the east-west and north-south directions. Aspect was also grouped into eight 45° classes (N, NE, E, SE, S, SW, W, NW) and expressed as one-hot indicators. The slope was stored as `Slope_sin` and `Slope_cos`. However, `Slope_sin` lies between {{facts.quality.slope_sin_min:.6f}} and {{facts.quality.slope_sin_max:.1f}} for every spring, which corresponds to a slope of about 90° everywhere and indicates an error in the slope derivation (for example, slope computed on a DEM in geographic degrees without metre scaling). The slope variables therefore carry no information and are not interpreted in this report. Elevation, slope and aspect are not predictors in the proposal-compliant models.

Springs are concentrated at mid-elevations (median {{facts.elevation.median:.0f}} m; {{facts.elevation.springs_by_band["1400-1700"]:,}} of {{facts.n_springs:,}} springs lie between 1,400 and 1,700 m; [[fig:elev]]). The share of dried springs decreases with elevation, from {{facts.elevation.dried_pct_by_band["<1000"]:.1f}}% below 1,000 m and {{facts.elevation.dried_pct_by_band["1000-1400"]:.1f}}% between 1,000 and 1,400 m to {{facts.elevation.dried_pct_by_band["1400-1700"]:.1f}}% between 1,400 and 1,700 m and {{facts.elevation.dried_pct_by_band["1700-2000"]:.1f}}% between 1,700 and 2,000 m ({{facts.elevation.dried_pct_by_band[">2000"]:.1f}}% above 2,000 m, where springs are few). By aspect, the share of dried springs is lowest on east- and north-east-facing slopes ({{facts.aspect.dried_pct.E:.1f}}% and {{facts.aspect.dried_pct.NE:.1f}}%) and highest on south-west-, south- and west-facing slopes ({{facts.aspect.dried_pct.SW:.1f}}%, {{facts.aspect.dried_pct.S:.1f}}% and {{facts.aspect.dried_pct.W:.1f}}%; [[fig:aspect]], [[fig:polar]]).

![Spring condition across 100 m elevation bins.](overview_elevation_bins.png){#fig:elev width=0.95}

![(a) Active and dried springs per aspect class; (b) share of springs in each aspect class that are dried, with the overall share as a dashed line.](overview_aspect.png){#fig:aspect width=0.95}

![Active and dried springs by aspect (angle, north at the top) and elevation (radius, m).](overview_elevation_aspect_polar.png){#fig:polar width=0.65}

## Land use and land cover (ICIMOD) {#sec:lulc}

The ICIMOD regional land-cover product was used to characterise the surroundings of each spring. Land cover influences infiltration, evapotranspiration, soil-moisture retention, runoff generation and human disturbance [@jayawickreme2007; @bosmans2017], and in mountain environments it reflects slope modification, deforestation and cultivation pressure that affect spring recharge [@pant2026]. Land cover was summarised within a 1 km buffer around each spring rather than at the spring point, because spring discharge is influenced by a contributing area wider than the emergence point [@dreiss1983]. Within each buffer, pixel counts per class were converted to percentage cover. For dried springs, the land-cover year closest to the reported drying year was used.

Land cover is excluded as a modelled predictor for two reasons. Future land-cover datasets corresponding to the SSP scenarios planned for the dissertation are unavailable, which would make historical training and future projection data inconsistent. In addition, the historical product covers only 2000 to 2022, so springs that dried before 2000 cannot be assigned a representative land-cover condition, and the missing values would be correlated with the label. Land cover is retained as contextual background only.

## Geological data {#sec:geology}

Geological and lithological attributes were extracted from the geological map of the study area. Spring occurrence is controlled by rock type, fracture density, permeability and the contrast between aquifers and aquitards [@ra2018; @doctor2008]. Each spring was spatially joined to the geological polygon in which it occurs, and the corresponding formation and rock type were assigned as categorical attributes ({{facts.quality.n_missing_formation}} springs have no formation). Geological variables were not used as predictors because the mapped formations are coarse and extend over large areas, leaving many neighbouring springs with identical geological attributes.

## Road and infrastructure data {#sec:roads}

Road construction can alter slope stability, intercept shallow groundwater, redirect runoff and fragment recharge areas [@dutton2005; @montgomery1994]. Roads were analysed within a 1 km buffer around each spring and counted by eight compass sectors (`Road-N` to `Road-NW`), since roads upslope, downslope or lateral to a spring may have different hydrological effects. Dried springs have a higher mean number of road crossings than active springs in {{len(facts.roads.directions_dried_higher)}} of the 8 directions (all except north), and a higher mean total ({{facts.roads.mean_total_dried:.2f}} against {{facts.roads.mean_total_active:.2f}} crossings; [[fig:roads]]). These are descriptive associations, not evidence of an independent or causal effect, and road variables are not predictors in the proposal-compliant model.

![Mean road crossings within a 1 km buffer by direction for active and dried springs.](overview_road_crossings.png){#fig:roads width=0.9}

## Climate reanalysis data (ERA5-Land) {#sec:era5}

Climate data were obtained from the ERA5-Land reanalysis [@munozsabater2021], the land-surface component of ERA5 [@hersbach2020]. The NetCDF file used covers {{climate.era5.first_month[:7]}} to {{climate.era5.last_month[:7]}} ({{climate.era5.n_months}} monthly time steps) on a {{climate.era5.lat_res:.1f}}° grid (about 9 to 11 km) over 0 to 40° N and 60 to 100° E, with four variables: 2 m air temperature (`t2m`), 2 m dewpoint temperature (`d2m`), total precipitation (`tp`) and potential evaporation (`pev`). The {{facts.n_springs:,}} springs fall within only {{facts.grid.n_cells}} ERA5-Land grid cells (between {{facts.grid.springs_per_cell_min}} and {{facts.grid.springs_per_cell_max:,}} springs per cell), so all springs within a cell receive identical climate values. As discussed in [[sec:lit-reanalysis]], these values represent regional climate forcing, with temperature more reliable than precipitation [@khadka2022; @lavers2022].

### Extraction and temporal aggregation

For each spring, the nearest ERA5-Land grid cell was selected; nearest-cell extraction avoids interpolation artefacts and is reproducible. The monthly series were averaged to calendar years, using complete years only. Temperature and dewpoint were converted from kelvin to °C. Precipitation and potential evaporation, stored as monthly means of daily accumulations in metres, were converted to millimetres per year (multiplying by 1,000 and by 365). Potential evaporation was also multiplied by −1 to remove the ECMWF sign convention (negative values denote evaporation), so that larger values mean greater evaporative demand.

### Trend estimation and 15-year summary

Temporal trends were estimated with the non-parametric Mann-Kendall test [@mann1945], which detects monotonic trends without assuming a distribution, and their magnitude with Sen's slope [@sen1968], the median of all pairwise slopes, which is insensitive to outliers. The slope, rather than its statistical significance, is used as the predictor because the aim is to encode the magnitude and direction of change at each location. The 15-year mean of each variable was computed over the same window. Each spring therefore has eight climate features: four trends (`Dewpoint_rate`, `Temperature_rate`, `Precipitation_rate`, `Evaporation_rate`) and four means (`Dewpoint_mean`, `Temperature_mean`, `Precipitation_mean`, `Evaporation_mean`).

### Climate window definition: two versions {#sec:windows}

**Version A (label-conditional window).** An active spring uses the 15 years ending in the survey year ({{climate.window.replace("-", " to ")}}); a dried spring uses the 15 years ending at its own reported drying year. A complete window requires an end year of at least {{facts.drying_year.first_complete_window_end}} (ERA5-Land begins in 1950), so {{climate.version_a_too_early}} springs that dried earlier and {{climate.version_a_missing_year}} dried springs without a recorded year have no Version A features, leaving {{climate.version_a_valid_rows:,}} springs. The design was intended to describe each spring over the period most relevant to its status, but it leaks the label ([[sec:leakage]]).

**Version B (fixed window).** Every spring, active or dried, uses the same window ({{climate.window.replace("-", " to ")}}), which ends in the survey year. The features then describe each location's recent climate independently of when or whether the spring dried. Using a common window for all classes follows the principle that predictor construction must not depend on information that is only known because the outcome is known [@kaufman2011].

[[fig:windows]] shows why the two versions behave so differently. Regional temperature varies from year to year and is higher in recent decades (the 2010s average {{climate.warming_1950s_to_2010s:.2f}} °C warmer than the 1950s across the {{facts.grid.n_cells}} cells), while the windows of dried springs end in many different years, mostly before the survey year that ends every active spring's window.

![Top: ERA5-Land annual mean temperature averaged over the 12 cells containing Roshi springs, with the fixed Version B window shaded. Bottom: reported drying years, which set the end of the Version A window for dried springs.](climate_timeseries_windows.png){#fig:windows width=0.95}

Under Version A, the climate distributions of active and dried springs differ strongly, especially for the trends ([[fig:distA]]). The median precipitation trend, for example, is {{climate.medians_version_a.Precipitation_rate.active:.1f}} mm/yr per year for active springs but {{climate.medians_version_a.Precipitation_rate.dried:.1f}} for dried springs, and the median temperature trend is {{climate.medians_version_a.Temperature_rate.active:.4f}} against {{climate.medians_version_a.Temperature_rate.dried:.4f}} °C per year. Under Version B the trend distributions of the two classes almost coincide (median precipitation trend {{climate.medians_version_b.Precipitation_rate.active:.1f}} against {{climate.medians_version_b.Precipitation_rate.dried:.1f}}; [[fig:distB]]), while differences in the 15-year means remain (median temperature mean {{climate.medians_version_b.Temperature_mean.active:.2f}} °C for active and {{climate.medians_version_b.Temperature_mean.dried:.2f}} °C for dried springs). Most of the separation seen under Version A is therefore a product of the window timing, not of climate at the springs. The submitted version of this report interpreted the Version A distributions as evidence of "tipping points" and of evaporative demand as "the primary driver" of drying; those interpretations are withdrawn.

![Climate features by spring condition under Version A (label-conditional window). Each class sums to 100%.](climate_distribution_version_a.png){#fig:distA width=0.85}

![Climate features by spring condition under Version B (fixed window, 2009 to 2023). Each class sums to 100%.](climate_distribution_version_b.png){#fig:distB width=0.85}

## Dataset assembly {#sec:assembly}

All layers were consolidated into one master table of {{facts.n_springs:,}} springs combining spring attributes, terrain derivatives, land-cover summaries, geological attributes, road-network counts and climate means and trends ([[tab:datasets]]). The climate features used in this report are recomputed by the project code for both window versions rather than taken from the master table (Appendix A).

Table: Datasets used to build the analysis table {#tab:datasets cols=LLLLL size=footnotesize}
| Dataset | Spatial resolution | Temporal resolution | Key variables | Role in analysis |
|---|---|---|---|---|
| Spring inventory [@thapa2025] | Point | Single survey, 2023 to 2024 | location, condition, perennial/seasonal, drying year, reason of drying | Sample, labels and spring type |
| Watershed boundary | Polygon | Static | Roshi Khola basin outline | Restricts analysis to the catchment |
| SRTM DEM | Raster | Static | elevation | Elevation, slope, aspect (context) |
| ICIMOD land cover | Raster | Multi-year, 2000 to 2022 | land-cover classes | 1 km buffer composition (context) |
| Geological map | Polygon | Static | formation, rock type | Geology per spring (context) |
| Road network | Vector | Static | roads by direction sector | Infrastructure pressure (context) |
| ERA5-Land | {{climate.era5.lat_res:.1f}}° grid | Monthly, 1950 to 2026, aggregated to years | t2m, d2m, tp, pev | Climate means and trends (predictors) |

## Pre-processing and feature engineering {#sec:prep}

Source condition was encoded as a binary label (dried = 1, active = 0) and spring type as a binary feature (perennial = 1, seasonal = 0). Under Version A, {{facts.n_springs - climate.version_a_valid_rows}} springs without a complete window were excluded, leaving {{climate.version_a_valid_rows:,}}; under Version B every spring has a complete window and all {{facts.n_springs:,}} are used. The reported cause of drying was attached to each dried spring for the label-screening analysis of [[sec:m3b]]. The proposal also specifies screening dried labels by how long ago the spring dried; that persistence screening is carried forward to the dissertation phase ([[sec:future]]).

# Modelling Methodology {#sec:method}

## Predictor scope

Following the finalised proposal, the climate predictors derived from ERA5-Land and the perennial/seasonal spring attribute form the modelled feature set. Land cover, geology and road-network layers are not predictors in the proposal-compliant model. Two earlier exploratory models that also include terrain and road variables are documented in [[sec:results]] for transparency; they are not the project's primary result. [[tab:design]] lists all model configurations.

Table: Model configurations evaluated in this report {#tab:design cols=lLLLr size=footnotesize}
| Model | Climate window | Predictors | Labels | Springs |
|---|---|---|---|---|
| Model 1 (exploratory) | Version A | {{m1.n_features_in}}: 8 climate, spring type, elevation, aspect (degrees and 8 classes), 8 road counts, 2 slope terms | all dried vs active | {{m1.n_rows:,}} |
| Model 2 (refined) | Version A | {{m2.n_features_in}}: 6 climate (no evaporation), spring type, elevation, aspect, 8 road counts | all dried vs active | {{m2.n_rows:,}} |
| Model 3 (Version A) | Version A | 8 climate + spring type, VIF-screened | all dried vs active | {{m3va.n_rows:,}} |
| **Model 3** (primary) | Version B | 8 climate + spring type, VIF-screened | all dried vs active | {{m3.n_rows:,}} |
| Spring type only | none | spring type | all dried vs active | {{type.n_rows:,}} |
| Climate only | Version B | 8 climate, VIF-screened | all dried vs active | {{clim.n_rows:,}} |
| **Model 3b** | Version B | 8 climate + spring type, VIF-screened | drought-dried vs active | {{m3b.n_rows:,}} |
| Model 3b, climate only | Version B | 8 climate, VIF-screened | drought-dried vs active | {{m3bc.n_rows:,}} |
| Earthquake contrast | Version B | 8 climate + spring type, VIF-screened | earthquake-dried vs active | {{eq.n_rows:,}} |

## Multicollinearity screening (variance inflation factor)

Multicollinearity screening with the variance inflation factor (VIF) was applied to the climate predictors. For each candidate predictor xᵢ, the candidates were standardised, xᵢ was regressed on all other candidates by ordinary least squares, and

$$ \mathrm{VIF}_i = \frac{1}{1 - R_i^2} $$ || VIFᵢ = 1 / (1 − Rᵢ²)

was computed, where Rᵢ² is the coefficient of determination of that regression. The predictor with the highest VIF was dropped and the VIFs recomputed until all remaining climate predictors had VIF ≤ 10 or only two remained. The screening is the first step of the modelling pipeline, so in every train/test split and every cross-validation fold it is fitted on the training springs only. It is used as a pragmatic redundancy-control step, not as a claim that Random Forest requires independent predictors; collinearity mainly complicates the interpretation of variable importance and the transfer of models to places or times with a different correlation structure [@dormann2013].

## Train/test split, cross-validation and new-area test

Each configuration was evaluated in three ways:

1. **Held-out test set.** A stratified 70/30 split (`random_state = 42`) preserves the class ratio in both partitions. Stratification matters because the dried class is the minority and accuracy can be dominated by the majority class [@he2009].
2. **Shuffled stratified 5-fold cross-validation.** Five folds with shuffling (`random_state = 42`), reported as mean ± standard deviation over the folds. The submitted version used unshuffled folds; because the dataset file is ordered, the share of dried springs in unshuffled folds ranges from {{min(checks.dried_pct_by_file_fifth):.1f}}% to {{max(checks.dried_pct_by_file_fifth):.1f}}% ([[sec:m3]]).
3. **New-area test (leave-one-grid-cell-out).** Each of the {{facts.grid.n_cells}} ERA5-Land cells is held out in turn, the model is trained on springs in the other cells, and the pooled out-of-fold ROC-AUC is reported. The test shows how far performance depends on having seen the same location, and hence the same climate values, during training [@roberts2017; @wenger2012].

## Random Forest classifier

A Random Forest classifier [@breiman2001] was used throughout. A Random Forest is an ensemble of decision trees, each trained on a bootstrap sample of the training data with a random subset of features considered at each split, and predictions are aggregated by voting. Averaging over many trees reduces the variance of individual trees while retaining non-linear relationships and interactions. The configuration was the same for all models: 2,000 trees, `class_weight = "balanced"` (which weights each dried spring about {{facts.n_active/facts.n_dried:.1f}} times as heavily as each active spring, the inverse of the class frequencies) and `random_state = 42`. A `StandardScaler` step is kept for continuity with the earlier work, although it has no effect on tree-based models. The proposal specifies SMOTE [@chawla2002] and class weighting for the multi-algorithm comparison of the dissertation. This report uses class weighting only, and any oversampling in the dissertation will be applied within training folds only [@santos2018].

## Evaluation metrics and variable importance

The positive class is dried (label 1) throughout. With TP, TN, FP and FN the numbers of true positives, true negatives, false positives and false negatives:

$$ \mathrm{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}, \quad \mathrm{Precision} = \frac{TP}{TP + FP}, \quad \mathrm{Recall} = \frac{TP}{TP + FN} $$ || Accuracy = (TP + TN) / (TP + TN + FP + FN);  Precision = TP / (TP + FP);  Recall = TP / (TP + FN)

$$ F_1 = \frac{2 \cdot \mathrm{Precision} \cdot \mathrm{Recall}}{\mathrm{Precision} + \mathrm{Recall}} $$ || F1 = 2 · Precision · Recall / (Precision + Recall)

The ROC-AUC is the area under the receiver operating characteristic curve. It equals the probability that a randomly chosen dried spring receives a higher predicted probability of drying than a randomly chosen active spring (0.5 for random ranking, 1 for perfect ranking). Because the response is imbalanced, recall and F1 for the dried class are reported alongside ROC-AUC rather than relying on accuracy [@he2009; @saito2015]. The PR-AUC (average precision) summarises precision over all levels of recall; unlike ROC-AUC, its value for random ranking equals the share of dried springs in the test set ({{m3.test_prevalence:.3f}} for Model 3), so it is read against that baseline [@saito2015]. To show how much the test-set values depend on which springs happen to be in the test set, 95% confidence intervals for the test ROC-AUC and PR-AUC were obtained by a percentile bootstrap: the test springs were resampled with replacement 2,000 times and both measures recomputed for the fitted model.

Variable importance is reported in two forms: the Random Forest's impurity-based importance, and permutation importance, the mean drop in test-set ROC-AUC when one predictor is randomly shuffled (10 repeats). Permutation importance is measured on unseen springs and is less affected by the biases of impurity-based importance [@strobl2007].

![Methodological workflow of the project.](methodology_flowchart.png){#fig:flow width=0.8}

# Model Development and Results {#sec:results}

Five model configurations were developed in sequence, plus comparison and sensitivity runs ([[tab:design]]). Models 1 and 2 were exploratory and progressively narrowed the feature set. Model 3 was built to match the proposal and was first run with the Version A window. The near-perfect scores of these three models led to the leakage diagnosis of [[sec:leakage]], after which Model 3 was re-run with the fixed Version B window; that run is the primary result. All results below come from the reproducible notebooks listed in Appendix A.

## Model 1: exploratory full-feature model {#sec:m1}

Model 1 was an initial broad feature-screening model, built before the proposal excluded terrain and roads from the predictor set. It uses {{m1.n_features_in}} predictors: spring type, elevation, aspect in degrees and as eight one-hot classes, eight directional road counts, the two slope terms and the eight Version A climate features, without VIF screening. In the submitted version, every predictor was cast to an integer before training, which truncated the dewpoint, temperature and evaporation trends, the evaporation mean and `Slope_cos` to zero. That error has been corrected here, so the figures below differ from those submitted.

Model 1 reaches accuracy {{m1.test.accuracy:.3f}}, F1 {{m1.test.f1:.3f}} and ROC-AUC {{m1.test.roc_auc:.3f}} on the test set ([[tab:versionA]], [[fig:m1cm]]), with only {{m1.confusion.fp}} active springs misclassified as dried and {{m1.confusion.fn}} dried springs missed. Its most important predictors are climate trend features (`Evaporation_rate` {{100*m1.importance_impurity.Evaporation_rate:.1f}}%, `Temperature_rate` {{100*m1.importance_impurity.Temperature_rate:.1f}}% of impurity importance; [[fig:m1imp]]).

![Model 1: confusion matrix and ROC curve on the held-out test set.](model1_exploratory_confusion_roc.png){#fig:m1cm width=0.95}

![Model 1: impurity and permutation importance of the 15 most important predictors.](model1_exploratory_feature_importance.png){#fig:m1imp width=0.95}

## Model 2: refined feature set {#sec:m2}

Model 2 narrowed the feature set of Model 1 towards the variables that could be used in the planned scenario projections. Land cover and geology were not used (land cover cannot be projected consistently with the SSP scenarios and is missing before 2000; the geological map is too coarse), the evaporation mean and trend were removed, and the degenerate slope terms were left out. The submitted version justified removing evaporation by its low importance in Model 1. That low importance was an artefact of the integer casting described above: with the error corrected, `Evaporation_rate` is the most important predictor of Model 1. The original Model 2 code was not archived, so Model 2 was re-created from its description; it uses {{m2.n_features_in}} predictors.

Model 2 performs almost identically to Model 1 (accuracy {{m2.test.accuracy:.3f}}, F1 {{m2.test.f1:.3f}}, ROC-AUC {{m2.test.roc_auc:.3f}}; [[tab:versionA]], [[fig:m2cm]]). Its most important predictors are again climate trends (`Temperature_rate` {{100*m2.importance_impurity.Temperature_rate:.1f}}%, `Dewpoint_rate` {{100*m2.importance_impurity.Dewpoint_rate:.1f}}%; [[fig:m2imp]]). In the submitted version, the confusion-matrix figure shown for Model 2 was the same image as that of Model 1.

![Model 2: confusion matrix and ROC curve on the held-out test set.](model2_refined_confusion_roc.png){#fig:m2cm width=0.95}

![Model 2: impurity and permutation importance of the 15 most important predictors.](model2_refined_feature_importance.png){#fig:m2imp width=0.95}

## Model 3 with the Version A window {#sec:m3va}

Model 3 implements the proposal's predictor set: the eight climate features and spring type, with VIF screening. With the Version A window, the screening removed `Dewpoint_mean` (VIF {{m3va.vif.dropped[0][1]:.1f}}) and the model reached accuracy {{m3va.test.accuracy:.3f}}, F1 {{m3va.test.f1:.3f}} and ROC-AUC {{m3va.test.roc_auc:.3f}} ([[tab:versionA]], [[fig:m3vacm]]), with `Evaporation_rate` ({{100*m3va.importance_impurity.Evaporation_rate:.1f}}%) and `Temperature_rate` ({{100*m3va.importance_impurity.Temperature_rate:.1f}}%) as the leading predictors ([[fig:m3vaimp]]). In the submitted version these near-perfect values were attributed to Model 2.

Table: Results of the three models built on Version A climate features (test set n = {{m1.n_test}}, of which {{m1.n_test_dried}} dried; cross-validation over {{m1.n_rows:,}} springs) {#tab:versionA cols=LRRR}
| Metric | Model 1 | Model 2 | Model 3 (Version A) |
|---|---|---|---|
| Accuracy | {{m1.test.accuracy:.3f}} | {{m2.test.accuracy:.3f}} | {{m3va.test.accuracy:.3f}} |
| Precision | {{m1.test.precision:.3f}} | {{m2.test.precision:.3f}} | {{m3va.test.precision:.3f}} |
| Recall | {{m1.test.recall:.3f}} | {{m2.test.recall:.3f}} | {{m3va.test.recall:.3f}} |
| F1 | {{m1.test.f1:.3f}} | {{m2.test.f1:.3f}} | {{m3va.test.f1:.3f}} |
| ROC-AUC | {{m1.test.roc_auc:.3f}} | {{m2.test.roc_auc:.3f}} | {{m3va.test.roc_auc:.3f}} |
| 5-fold CV F1 (mean ± sd) | {{m1.cv.f1_mean:.3f}} ± {{m1.cv.f1_sd:.3f}} | {{m2.cv.f1_mean:.3f}} ± {{m2.cv.f1_sd:.3f}} | {{m3va.cv.f1_mean:.3f}} ± {{m3va.cv.f1_sd:.3f}} |
| 5-fold CV ROC-AUC (mean ± sd) | {{m1.cv.auc_mean:.3f}} ± {{m1.cv.auc_sd:.3f}} | {{m2.cv.auc_mean:.3f}} ± {{m2.cv.auc_sd:.3f}} | {{m3va.cv.auc_mean:.3f}} ± {{m3va.cv.auc_sd:.3f}} |

![Model 3 with the Version A window: confusion matrix and ROC curve on the held-out test set.](model3_version_a_confusion_roc.png){#fig:m3vacm width=0.95}

![Model 3 with the Version A window: impurity and permutation importance.](model3_version_a_feature_importance.png){#fig:m3vaimp width=0.95}

## Discovery of the temporal leakage in the Version A window {#sec:leakage}

ROC-AUC values of {{min(m1.test.roc_auc, m2.test.roc_auc, m3va.test.roc_auc):.3f}} to {{max(m1.test.roc_auc, m2.test.roc_auc, m3va.test.roc_auc):.3f}} are implausibly high for a real-world hydrological classification task based on regional climate data, and they warranted scrutiny rather than acceptance.

The cause lies in the construction of the Version A window. Every active spring's window ends in the survey year, {{climate.window[-4:]}}, whereas a dried spring's window ends in its own drying year, which for most dried springs is earlier (median {{facts.drying_year.median:.0f}}; only {{checks.n_dried_ending_in_survey_year}} dried springs dried in {{climate.window[-4:]}}). The calendar period from which a spring's climate features are drawn is therefore almost mechanically determined by its label. Because regional climate varies from year to year ([[fig:windows]]), climate summaries over different periods differ systematically, and the model can learn the period of the window rather than any relationship between climate and spring status. In the terms of @kaufman2011, the predictors were constructed using information (the drying year) that is only available because the outcome is known, which is target leakage.

A direct diagnostic confirms the explanation. A Random Forest given only one input, the end year of each spring's Version A window, with no climate information at all, classifies the test springs with accuracy {{checks.leakage_diagnostic.accuracy:.3f}}, F1 {{checks.leakage_diagnostic.f1:.3f}} and ROC-AUC {{checks.leakage_diagnostic.roc_auc:.3f}}. The near-perfect performance of Models 1, 2 and 3 (Version A) is therefore an artefact of predictor construction. The dominance of the trend features fits this explanation, since trends are the features most sensitive to the choice of period. The correction is to give every spring the same window (Version B).

## Model 3 with the fixed window (primary result) {#sec:m3}

With the fixed window ({{climate.window.replace("-", " to ")}}), the VIF screening on the training springs removed `Dewpoint_mean` (VIF {{m3.vif.dropped[0][1]:.1f}}) and then `Evaporation_mean` (VIF {{m3.vif.dropped[1][1]:.1f}} after the first removal), leaving six climate predictors with VIFs between {{min(m3.vif.final.values()):.2f}} and {{max(m3.vif.final.values()):.2f}} ([[tab:vif]]). Together with spring type, Model 3 therefore uses `Dewpoint_rate`, `Temperature_rate`, `Precipitation_rate`, `Evaporation_rate`, `Temperature_mean`, `Precipitation_mean` and the perennial/seasonal attribute.

Table: VIF of the Version B climate predictors in the Model 3 training data, before screening and after the two removals {#tab:vif cols=LRR}
| Predictor | Initial VIF | Final VIF |
|---|---|---|
| Dewpoint_mean | {{m3.vif.initial.Dewpoint_mean:.1f}} | removed (1st) |
| Temperature_mean | {{m3.vif.initial.Temperature_mean:.1f}} | {{m3.vif.final.Temperature_mean:.2f}} |
| Evaporation_mean | {{m3.vif.initial.Evaporation_mean:.1f}} | removed (2nd) |
| Precipitation_rate | {{m3.vif.initial.Precipitation_rate:.1f}} | {{m3.vif.final.Precipitation_rate:.2f}} |
| Evaporation_rate | {{m3.vif.initial.Evaporation_rate:.1f}} | {{m3.vif.final.Evaporation_rate:.2f}} |
| Precipitation_mean | {{m3.vif.initial.Precipitation_mean:.1f}} | {{m3.vif.final.Precipitation_mean:.2f}} |
| Dewpoint_rate | {{m3.vif.initial.Dewpoint_rate:.1f}} | {{m3.vif.final.Dewpoint_rate:.2f}} |
| Temperature_rate | {{m3.vif.initial.Temperature_rate:.1f}} | {{m3.vif.final.Temperature_rate:.2f}} |

On the held-out test set ({{m3.n_test}} springs, {{m3.n_test_dried}} dried), Model 3 achieved the results in [[tab:m3]]. In the confusion matrix ([[fig:m3cm]]), {{m3.confusion.tn}} of {{m3.confusion.tn + m3.confusion.fp}} active springs are correctly classified and {{m3.confusion.fp}} are misclassified as dried, while {{m3.confusion.tp}} of {{m3.confusion.tp + m3.confusion.fn}} dried springs are correctly identified and {{m3.confusion.fn}} are missed.

Table: Model 3 (fixed window): test-set, cross-validation and new-area results {#tab:m3 cols=LR}
| Measure | Value |
|---|---|
| Accuracy (test) | {{m3.test.accuracy:.3f}} |
| Precision (test) | {{m3.test.precision:.3f}} |
| Recall (test) | {{m3.test.recall:.3f}} |
| F1 (test) | {{m3.test.f1:.3f}} |
| ROC-AUC (test) | {{m3.test.roc_auc:.3f}} |
| ROC-AUC (test), 95% bootstrap CI | {{m3.test_ci.roc_auc[0]:.3f}} to {{m3.test_ci.roc_auc[1]:.3f}} |
| PR-AUC (test; random ranking = {{m3.test_prevalence:.3f}}) | {{m3.test.pr_auc:.3f}} |
| PR-AUC (test), 95% bootstrap CI | {{m3.test_ci.pr_auc[0]:.3f}} to {{m3.test_ci.pr_auc[1]:.3f}} |
| 5-fold CV F1, shuffled (mean ± sd) | {{m3.cv.f1_mean:.3f}} ± {{m3.cv.f1_sd:.3f}} |
| 5-fold CV ROC-AUC, shuffled (mean ± sd) | {{m3.cv.auc_mean:.3f}} ± {{m3.cv.auc_sd:.3f}} |
| New-area ROC-AUC (leave-one-grid-cell-out) | {{m3.new_area_auc:.3f}} |

![Model 3 (fixed window): confusion matrix and ROC curve on the held-out test set.](model3_final_confusion_roc.png){#fig:m3cm width=0.95}

**Cross-validation.** The submitted version reported a 5-fold cross-validated F1 of {{checks.cv_f1_unshuffled_mean:.3f}} ± {{checks.cv_f1_unshuffled_sd:.3f}}, obtained with folds taken in file order. The dataset file is ordered: the share of dried springs in its five consecutive fifths is {{", ".join(f"{v:.1f}%" for v in checks.dried_pct_by_file_fifth)}}, so unshuffled folds differ strongly in class balance, and one fold scored F1 {{min(checks.cv_f1_unshuffled_folds):.3f}}. With shuffled stratified folds the cross-validated F1 is {{m3.cv.f1_mean:.3f}} ± {{m3.cv.f1_sd:.3f}}, consistent with the test-set value. Most of the apparent instability in the submitted version came from the fold construction rather than from the model.

## What Model 3 learns {#sec:m3-imp}

Perennial/seasonal classification dominates both importance measures ([[tab:imp]], [[fig:m3imp]]). It accounts for {{100*m3.importance_impurity["Perennial / Seasonal"]:.1f}}% of impurity importance, and shuffling it lowers the test ROC-AUC by {{m3.importance_permutation["Perennial / Seasonal"]:.3f}}, whereas shuffling any single climate predictor changes the test ROC-AUC by at most {{max(abs(v) for k, v in m3.importance_permutation.items() if k != "Perennial / Seasonal"):.3f}}. The climate predictors are strongly redundant with one another, so the loss of one shuffled predictor can be compensated by the others; together they still carry information (see the comparison in [[sec:m3b]]).

Table: Model 3 variable importance {#tab:imp cols=LRR}
| Predictor | Impurity importance (%) | Permutation importance (ROC-AUC drop) |
|---|---|---|
| Perennial / Seasonal | {{100*m3.importance_impurity["Perennial / Seasonal"]:.1f}} | {{m3.importance_permutation["Perennial / Seasonal"]:.4f}} |
| Precipitation_rate | {{100*m3.importance_impurity.Precipitation_rate:.1f}} | {{m3.importance_permutation.Precipitation_rate:.4f}} |
| Temperature_mean | {{100*m3.importance_impurity.Temperature_mean:.1f}} | {{m3.importance_permutation.Temperature_mean:.4f}} |
| Temperature_rate | {{100*m3.importance_impurity.Temperature_rate:.1f}} | {{m3.importance_permutation.Temperature_rate:.4f}} |
| Precipitation_mean | {{100*m3.importance_impurity.Precipitation_mean:.1f}} | {{m3.importance_permutation.Precipitation_mean:.4f}} |
| Dewpoint_rate | {{100*m3.importance_impurity.Dewpoint_rate:.1f}} | {{m3.importance_permutation.Dewpoint_rate:.4f}} |
| Evaporation_rate | {{100*m3.importance_impurity.Evaporation_rate:.1f}} | {{m3.importance_permutation.Evaporation_rate:.4f}} |

![Model 3 (fixed window): impurity and permutation importance.](model3_final_feature_importance.png){#fig:m3imp width=0.95}

Because all springs in a grid cell share the same climate values, the {{facts.n_springs:,}} springs have only {{checks.n_distinct_rows}} distinct combinations of predictor values ({{facts.grid.n_cells}} cells × 2 spring types, where present), and {{checks.test_rows_seen_in_train_pct:.1f}}% of test springs have an exact counterpart in the training set. A simple lookup table that assigns each test spring the dried share of its predictor combination in the training set reaches a test ROC-AUC of {{checks.lookup_table_auc:.3f}}, the same as the Random Forest ({{m3.test.roc_auc:.3f}}). Model 3 therefore learns the dried rate of each grid cell for perennial and seasonal springs; it cannot distinguish springs within a cell that share a spring type.

## Input comparison and Model 3b: label screening by drying cause {#sec:m3b}

[[tab:compare]] and [[fig:compare]] compare Model 3 with models that use only spring type or only climate, and with models trained on subsets of the dried springs defined by their reported cause. Spring type alone reaches a test ROC-AUC of {{type.test.roc_auc:.3f}} and climate alone {{clim.test.roc_auc:.3f}}; together (Model 3) they reach {{m3.test.roc_auc:.3f}}, so each carries information the other does not.

Model 3b repeats Model 3 but keeps only the {{facts.drying_cause.drought}} springs whose drying was attributed to drought or reduced precipitation, compared with all {{facts.n_active:,}} active springs. Its test ROC-AUC is {{m3b.test.roc_auc:.3f}} (95% CI {{m3b.test_ci.roc_auc[0]:.3f}} to {{m3b.test_ci.roc_auc[1]:.3f}}; cross-validated {{m3b.cv.auc_mean:.3f}} ± {{m3b.cv.auc_sd:.3f}}), and with climate predictors alone {{m3bc.test.roc_auc:.3f}}, compared with {{clim.test.roc_auc:.3f}} for climate alone on all dried springs. The contrast model, which keeps only the {{facts.drying_cause.earthquake}} earthquake-attributed dried springs, reaches {{eq.test.roc_auc:.3f}} (95% CI {{eq.test_ci.roc_auc[0]:.3f}} to {{eq.test_ci.roc_auc[1]:.3f}}). The confidence intervals of Model 3b and Model 3 ({{m3.test_ci.roc_auc[0]:.3f}} to {{m3.test_ci.roc_auc[1]:.3f}}) do not overlap, nor do those of Model 3b and the earthquake contrast. Climate predictors therefore separate drought-dried springs from active springs better than they separate earthquake-dried springs. That is the physically expected direction: the climate signal is present but diluted when drying from non-climatic causes is mixed into the dried class.

Model 3b's F1 ({{m3b.test.f1:.3f}}) is lower than Model 3's even though its ROC-AUC is higher, because dried springs make up only {{100*m3b.n_dried/m3b.n_rows:.1f}}% of its data. With so few positives, the false alarms ({{m3b.confusion.fp}}) outnumber the correctly identified dried springs ({{m3b.confusion.tp}} of {{m3b.confusion.tp + m3b.confusion.fn}}), which lowers precision and F1. Its PR-AUC ({{m3b.test.pr_auc:.3f}}) is lower than Model 3's ({{m3.test.pr_auc:.3f}}) for the same reason, but relative to random ranking it is higher: {{m3b.test.pr_auc/m3b.test_prevalence:.1f}} times the {{m3b.test_prevalence:.3f}} expected by chance, against {{m3.test.pr_auc/m3.test_prevalence:.1f}} times for Model 3. ROC-AUC does not depend on class prevalence and is the appropriate measure for comparing these configurations ([[fig:m3bcm]]).

Table: Comparison of input sets and label screening by reported cause (test set: stratified 30%; CV: shuffled 5-fold; new area: leave-one-grid-cell-out) {#tab:compare cols=LRRRRRR size=footnotesize}
| Configuration | Springs (dried) | Test F1 | Test ROC-AUC | CV F1 | CV ROC-AUC | New-area ROC-AUC |
|---|---|---|---|---|---|---|
| Spring type only | {{type.n_rows:,}} ({{type.n_dried}}) | {{type.test.f1:.3f}} | {{type.test.roc_auc:.3f}} | {{type.cv.f1_mean:.3f}} | {{type.cv.auc_mean:.3f}} | {{type.new_area_auc:.3f}} |
| Climate only | {{clim.n_rows:,}} ({{clim.n_dried}}) | {{clim.test.f1:.3f}} | {{clim.test.roc_auc:.3f}} | {{clim.cv.f1_mean:.3f}} | {{clim.cv.auc_mean:.3f}} | {{clim.new_area_auc:.3f}} |
| **Model 3** (climate + type) | {{m3.n_rows:,}} ({{m3.n_dried}}) | {{m3.test.f1:.3f}} | {{m3.test.roc_auc:.3f}} | {{m3.cv.f1_mean:.3f}} | {{m3.cv.auc_mean:.3f}} | {{m3.new_area_auc:.3f}} |
| **Model 3b**: drought-dried vs active | {{m3b.n_rows:,}} ({{m3b.n_dried}}) | {{m3b.test.f1:.3f}} | {{m3b.test.roc_auc:.3f}} | {{m3b.cv.f1_mean:.3f}} | {{m3b.cv.auc_mean:.3f}} | {{m3b.new_area_auc:.3f}} |
| Model 3b, climate only | {{m3bc.n_rows:,}} ({{m3bc.n_dried}}) | {{m3bc.test.f1:.3f}} | {{m3bc.test.roc_auc:.3f}} | {{m3bc.cv.f1_mean:.3f}} | {{m3bc.cv.auc_mean:.3f}} | {{m3bc.new_area_auc:.3f}} |
| Earthquake-dried vs active | {{eq.n_rows:,}} ({{eq.n_dried}}) | {{eq.test.f1:.3f}} | {{eq.test.roc_auc:.3f}} | {{eq.cv.f1_mean:.3f}} | {{eq.cv.auc_mean:.3f}} | {{eq.new_area_auc:.3f}} |

![ROC-AUC of Model 3, the input comparisons and Model 3b on the test set, in shuffled 5-fold cross-validation and in the new-area (leave-one-grid-cell-out) test.](model3_comparison.png){#fig:compare width=0.95}

![Model 3b (drought-dried vs active springs): confusion matrix and ROC curve on the held-out test set.](model3b_drought_confusion_roc.png){#fig:m3bcm width=0.95}

## Performance in unseen areas {#sec:newarea}

When whole grid cells are held out, performance falls for every configuration ([[tab:compare]], orange bars in [[fig:compare]]). Model 3 reaches a new-area ROC-AUC of {{m3.new_area_auc:.3f}}, compared with {{m3.test.roc_auc:.3f}} on the random test split, and climate alone falls to {{clim.new_area_auc:.3f}}, close to random ranking. Model 3b keeps a new-area ROC-AUC of {{m3b.new_area_auc:.3f}}, but with climate predictors alone it falls to {{m3bc.new_area_auc:.3f}}, so in unseen areas its skill comes mainly from spring type. With only {{facts.grid.n_cells}} distinct climate locations, the climate predictors identify which cell a spring is in, and a model trained on the other cells has no basis to rank the springs of a new cell by climate. It is the main limitation of the current climate inputs ([[sec:limits]]).

# Discussion {#sec:discussion}

## Descriptive spatial, terrain and infrastructure findings

Springs in the Roshi Khola watershed are concentrated at mid-elevations. The share of dried springs decreases with elevation and is lower on east- and north-east-facing slopes than on south-, south-west- and west-facing slopes ([[sec:topo]]), a pattern consistent with the influence of solar radiation and evaporative demand on moisture retention [@gutierrez2013; @broxton2009]. Dried springs also have more road crossings within 1 km in seven of eight directions, consistent with the capacity of road construction to intercept shallow groundwater and redirect runoff [@montgomery1994; @dutton2005]. These are descriptive associations: elevation, aspect, roads and climate are correlated across the watershed, and none of these patterns is evidence of an independent or causal effect.

## Interpretation of model performance {#sec:interpret}

The corrected model predicts spring status better than chance, with a test ROC-AUC of {{m3.test.roc_auc:.3f}} and a cross-validated ROC-AUC of {{m3.cv.auc_mean:.3f}} ± {{m3.cv.auc_sd:.3f}}, against 0.5 for random ranking. The result gives modest support to the within-watershed part of the working hypothesis, and the support is limited for three reasons. First, the perennial/seasonal attribute carries most of the signal. That is physically expected, because seasonal springs are more susceptible to running dry, but it also means that climate adds comparatively little once spring type is known. Second, the climate predictors take only {{facts.grid.n_cells}} distinct values and act as a location identifier; Model 3 is equivalent to a lookup table of the dried rate per grid cell and spring type ([[sec:m3-imp]]). Third, performance drops in unseen grid cells ([[sec:newarea]]). Climate variables and spring type thus contain a moderate within-watershed signal, but the model does not establish a causal climate effect and is not suitable for high-confidence operational use.

The label-screening result qualifies this reading. The climate signal is clearer when only drought-dried springs are compared with active springs (Model 3b), and weaker for earthquake-dried springs. In this inventory {{facts.drying_cause.earthquake}} of {{facts.n_dried}} dried springs ({{100*facts.drying_cause.earthquake/facts.n_dried:.1f}}%) are attributed to the earthquake, and most of them dried in 2015. The pattern agrees with the immediate drying effect of the 2015 earthquake reported in the Melamchi area [@chapagain2019] and with the multiple causes perceived by local governments [@thapa2023]. A climate-driven model of spring drying should therefore be trained on labels that reflect climate-related drying.

## Comparison with the literature {#sec:compare-lit}

Published results are useful here only as broad plausibility references, because prediction targets, predictors, sampling units and validation designs differ ([[tab:literature]]). The test ROC-AUC of Model 3 ({{m3.test.roc_auc:.3f}}) is of the same order as held-out values reported for related Random Forest tasks, such as 0.748 for water-spring potential in Jordan [@alshabeeb2023] and 0.757 for a Random Forest groundwater-potential model without climate factors [@guo2023]. It is above the prediction-rate AUC of 0.60 for frequency-ratio groundwater-potential mapping in Shivapuri, Nepal [@upadhyaya2024]. The submitted version compared Model 3 with the range of 0.65 to 0.80 from that study, but those values are success-rate AUCs computed on the mapping data. The closest analogue, active-versus-depleted classification of mapped springs in Mongolia [@ishikawa2025], reported ROC-AUC values of 0.84 to 0.86 with satellite and terrain predictors. @niraula2021 found that accuracy fell from 92% to 75% on an independent dataset, which parallels the drop observed here in unseen grid cells. The near-perfect values of the Version A models did not pass this plausibility check, which was one reason for the leakage investigation.

Table: Published performance of related tasks (values from the cited abstracts) {#tab:literature cols=LLLL size=footnotesize}
| Study | Task and data | Validation | Reported performance |
|---|---|---|---|
| @alshabeeb2023 | Water-spring potential, Jordan; 200 springs, 13 predictors | 70/30 split | ROC-AUC: RF 0.748, SVM 0.732, MARS 0.727, BRT 0.689 |
| @guo2023 | Groundwater potential (productive wells), Yinchuan Plain | held-out data | ROC-AUC: RF 0.757 without climate factors; climate factors +0.073 |
| @upadhyaya2024 | Groundwater potential, Shivapuri RM, Nepal; frequency ratio | success vs prediction rate | success-rate AUC 0.65 (FR), 0.80 (MFR); prediction-rate AUC 0.60 (both) |
| @niraula2021 | Spring occurrence, Central Himalaya; 621 springs, 815 non-springs | 80/20 split; independent dataset | accuracy 92% (Bootstrap Forest); 75% on independent data |
| @ishikawa2025 | Discharging vs depleted springs, Mongolia; 228 labelled springs | cross-validation | ROC-AUC 0.84 (LR), 0.86 (RF), 0.84 (SVM) |
| This project, Model 3 | Active vs dried springs, Roshi Khola; {{facts.n_springs:,}} springs | 70/30 split; 5-fold CV; new area | ROC-AUC {{m3.test.roc_auc:.3f}} (test), {{m3.cv.auc_mean:.3f}} (CV), {{m3.new_area_auc:.3f}} (new area) |

## Class imbalance and dried-spring recall

Model 3 recovers {{m3.confusion.tp}} of {{m3.n_test_dried}} dried springs in the test set (recall {{m3.test.recall:.3f}}) while producing {{m3.confusion.fp}} false positives among {{m3.confusion.tn + m3.confusion.fp}} active springs. The relatively low precision for the dried class reflects both the difficulty of the task and the imbalance of the data ({{facts.pct_dried:.1f}}% dried). Of the {{facts.n_dried}} dried springs, {{m3.n_test_dried}} (30%) are in the stratified test set. As Model 3b shows, F1 and precision fall further when the positive class becomes rarer, even if ranking improves. ROC-AUC is used to compare configurations for that reason. The precision-recall view [@saito2015] gives the same picture: Model 3's PR-AUC of {{m3.test.pr_auc:.3f}} (95% CI {{m3.test_ci.pr_auc[0]:.3f}} to {{m3.test_ci.pr_auc[1]:.3f}}) is about {{m3.test.pr_auc/m3.test_prevalence:.1f}} times the {{m3.test_prevalence:.3f}} of random ranking, a clear but modest gain.

## Limitations {#sec:limits}

- **Coarse climate inputs.** All springs fall in {{facts.grid.n_cells}} ERA5-Land cells, so climate values do not vary within a cell; the new-area ROC-AUC ({{m3.new_area_auc:.3f}}) is the more realistic estimate of performance at unseen locations. Reanalysis precipitation in mountain terrain is also biased [@khadka2022; @lavers2022].
- **Label quality.** Spring status comes from a single survey and community reports. Drying years and causes are recalled, a few drying years are inconsistent between calendars, and the persistence of drying is not verified.
- **Non-climatic drying.** About {{100*facts.drying_cause.earthquake/facts.n_dried:.0f}}% of dried springs are attributed to the 2015 earthquake and others to infrastructure, neglect or other causes; including them in the dried class dilutes the climate signal.
- **Spring type.** The perennial/seasonal attribute dominates the model. If dried springs were more likely to be recorded as seasonal, part of its importance could reflect the outcome itself; the survey protocol should be checked.
- **Random-split evaluation.** The test set and cross-validation use random splits, so they describe performance for springs in already-sampled cells. Duplicate springs across the split do not change the test ROC-AUC ({{checks.test_auc_without_dups:.3f}} without them), but the bootstrap intervals cover only test-set sampling, not the choice of split or of grid cells.
- **Single algorithm and no tuning.** Only Random Forest with fixed settings was evaluated; algorithm comparison is planned for the dissertation.

# Future Work {#sec:future}

## Label screening by cause and persistence

The proposal specifies screening dried labels by how long a spring has been dry, and this report adds screening by the reported cause of drying (Model 3b). The dissertation will combine both: define climate-relevant drying labels (drought or reduced precipitation), treat earthquake- and infrastructure-related drying separately, determine an empirical minimum drying duration, and report results with and without low-confidence labels.

## From one row per spring to a year-by-year design {#sec:augmentation}

The submitted version proposed a temporal augmentation in which each active spring contributes one row per year for 2015 to 2023 and each dried spring one row per year from its drying year to 2023, each with the 15-year window ending in that year. Computed on this dataset, that design would produce {{facts.augmentation.rows_active:,}} active and {{facts.augmentation.rows_dried:,}} dried rows, raising the dried share only from {{facts.pct_dried:.1f}}% to {{facts.augmentation.pct_dried_after:.1f}}%. It would also reintroduce leakage: {{facts.augmentation.dried_rows_before_2015:,}} dried rows ({{facts.augmentation.pct_dried_rows_before_2015:.1f}}%) fall in years before 2015, for which no active rows exist, so the row year would again predict the label. Rows for years after drying would also describe climate after the spring had already dried, which cannot explain its drying.

A more defensible use of the drying year is a discrete-time, year-by-year design. Each spring contributes one row per year while it is still flowing, labelled 1 in the year it dries and 0 otherwise, and leaves the data after drying; active springs contribute rows labelled 0 up to the survey year. Predictors are the climate conditions preceding each year (for example, rainfall and temperature anomalies over the previous one to three years). The design asks whether springs dry after dry or hot years, uses the large year-to-year variation in climate rather than the small differences between grid cells, and avoids both leakage problems. All rows of a spring, and preferably of a grid cell, must be kept in the same cross-validation fold [@roberts2017; @john2025].

## Finer climate inputs

Spring-to-spring climate variation can be introduced by adjusting temperature to each spring's elevation using the DEM, by using higher-resolution precipitation products, and by station-based bias correction of reanalysis values, given the known weaknesses of reanalysis precipitation in Himalayan terrain [@khadka2022; @lavers2022].

## Algorithm comparison

The dissertation will compare Random Forest with logistic regression, gradient boosting such as XGBoost [@chen2016], support vector machines and, if justified by the predictor set, neural networks, with SMOTE or class weighting applied within training folds only [@santos2018]. Such a comparison is only informative once the climate inputs vary at the spring scale; with the current {{checks.n_distinct_rows}} distinct predictor combinations, all algorithms reduce to the same lookup table.

## Staged generalisability testing

The {{facts.outside.n_springs:,}} springs outside the analysis dataset remain untouched for staged transfer tests, first in Panchkhal (near domain) and then in the remaining municipalities [@wenger2012]. Many of them lie in climate cells already used by Roshi springs ([[tab:outside]]): only {{facts.outside.by_municipality.Panchkhal.pct_in_new_cells:.1f}}% of Panchkhal's {{facts.outside.by_municipality.Panchkhal.springs}} springs fall in cells not used in training, and Panchkhal has a much higher dried share ({{facts.outside.by_municipality.Panchkhal.pct_dried:.1f}}%) than Roshi ({{facts.pct_dried:.1f}}%). Transfer results should therefore be reported separately for springs in new cells, and the difference in prevalence should be considered when interpreting precision and F1.

Table: Springs outside the analysis dataset by municipality (inventory records not among the 3,287 analysis springs) {#tab:outside cols=LRRRR size=footnotesize}
| Municipality | Springs | ERA5-Land cells | Springs in cells unused by Roshi springs (%) | Dried (%) |
|---|---|---|---|---|
| Panchkhal | {{facts.outside.by_municipality.Panchkhal.springs}} | {{facts.outside.by_municipality.Panchkhal.cells}} | {{facts.outside.by_municipality.Panchkhal.pct_in_new_cells:.1f}} | {{facts.outside.by_municipality.Panchkhal.pct_dried:.1f}} |
| Dhulikhel | {{facts.outside.by_municipality.Dhulikhel.springs}} | {{facts.outside.by_municipality.Dhulikhel.cells}} | {{facts.outside.by_municipality.Dhulikhel.pct_in_new_cells:.1f}} | {{facts.outside.by_municipality.Dhulikhel.pct_dried:.1f}} |
| Temal | {{facts.outside.by_municipality.Temal.springs}} | {{facts.outside.by_municipality.Temal.cells}} | {{facts.outside.by_municipality.Temal.pct_in_new_cells:.1f}} | {{facts.outside.by_municipality.Temal.pct_dried:.1f}} |
| Bethanchowk | {{facts.outside.by_municipality.Bethanchownk.springs}} | {{facts.outside.by_municipality.Bethanchownk.cells}} | {{facts.outside.by_municipality.Bethanchownk.pct_in_new_cells:.1f}} | {{facts.outside.by_municipality.Bethanchownk.pct_dried:.1f}} |
| Namobuddha | {{facts.outside.by_municipality.Namobuudha.springs}} | {{facts.outside.by_municipality.Namobuudha.cells}} | {{facts.outside.by_municipality.Namobuudha.pct_in_new_cells:.1f}} | {{facts.outside.by_municipality.Namobuudha.pct_dried:.1f}} |
| Roshi RM (outside the watershed) | {{facts.outside.by_municipality["Roshi RM"].springs}} | {{facts.outside.by_municipality["Roshi RM"].cells}} | {{facts.outside.by_municipality["Roshi RM"].pct_in_new_cells:.1f}} | {{facts.outside.by_municipality["Roshi RM"].pct_dried:.1f}} |
| Panauti | {{facts.outside.by_municipality.Panauti.springs}} | {{facts.outside.by_municipality.Panauti.cells}} | {{facts.outside.by_municipality.Panauti.pct_in_new_cells:.1f}} | {{facts.outside.by_municipality.Panauti.pct_dried:.1f}} |

## Explainability

SHAP values [@lundberg2017] will be computed for the best dissertation-phase model to show which climate or spring attributes push each spring's predicted probability towards active or dried. They will be read alongside permutation importance and interpreted as associations rather than causes [@strobl2007].

## Future climate scenario projection

The dissertation will project drying risk for the near term (2025 to 2050), mid term (2051 to 2075) and long term (2076 to 2100) under SSP2-4.5 and SSP5-8.5, using downscaled CMIP6 projections [@thrasher2022], and map the probability of drying for each spring. The projection should use a model trained on climate-relevant drying labels and on climate inputs that vary at the spring scale, because a model that has learned grid-cell identity cannot respond meaningfully to projected changes in climate.

# Conclusion {#sec:conclusion}

This project asked whether active and dried springs in the Roshi Khola watershed can be distinguished from climate variables and a spring-intrinsic characteristic using machine learning. It produced a {{facts.n_springs:,}}-spring analysis dataset assembled from the community spring inventory, SRTM terrain derivatives, ICIMOD land cover, geological maps, road-network attributes and ERA5-Land climate reanalysis, together with a reproducible code base in which every reported number is generated by the analysis notebooks.

The central methodological finding is the temporal leakage in the original label-conditional climate window. The window end year alone separated active and dried springs with ROC-AUC {{checks.leakage_diagnostic.roc_auc:.3f}}, so the near-perfect performance of the earlier models (ROC-AUC {{min(m1.test.roc_auc, m2.test.roc_auc, m3va.test.roc_auc):.3f}} to {{max(m1.test.roc_auc, m2.test.roc_auc, m3va.test.roc_auc):.3f}}) was an artefact of predictor construction. With a common window ({{climate.window.replace("-", " to ")}}) for every spring, Model 3 achieved accuracy {{m3.test.accuracy:.3f}}, F1 {{m3.test.f1:.3f}} and ROC-AUC {{m3.test.roc_auc:.3f}} on the test set and a cross-validated F1 of {{m3.cv.f1_mean:.3f}} ± {{m3.cv.f1_sd:.3f}}. The perennial/seasonal classification is the dominant predictor ({{100*m3.importance_impurity["Perennial / Seasonal"]:.1f}}% of impurity importance), and climate adds a smaller but real signal that becomes clearer when only drought-dried springs are considered (Model 3b, ROC-AUC {{m3b.test.roc_auc:.3f}}).

The analysis also shows the limits of the current design. The {{facts.n_springs:,}} springs share only {{facts.grid.n_cells}} ERA5-Land cells, so the climate predictors act as a location identifier and performance falls to ROC-AUC {{m3.new_area_auc:.3f}} in unseen cells; in addition, about {{100*facts.drying_cause.earthquake/facts.n_dried:.0f}}% of the dried springs are attributed to the 2015 earthquake. For the dissertation, climate predictors must be constructed independently of the label, labels should be screened for climate-related drying, and climate inputs must vary at the spring scale, ideally through a year-by-year design that uses the variation of climate over time. Algorithm comparison, transfer testing and scenario projection can only be interpreted once these conditions are met.

<<REFERENCES>>

<<APPENDIX>>

# Reproducibility {#sec:appendix-repro}

All results in this report are generated by the project repository. The large input files (the ERA5-Land NetCDF, the master analysis table and the raw survey export) are not stored in the repository; their location is set in `src/spring_drying/config.py`. The analysis runs in the order shown in [[tab:notebooks]], and each notebook writes its numbers to `results/tables/*.json` and its figures to `results/figures/`. The script `scripts/export_report_numbers.py` collects those numbers, and `scripts/build_report.py` builds this report (LaTeX and Word) from them, so no statistic in the report is typed by hand. References were checked against Crossref with `scripts/check_references.py` (result in `report/reference_check.csv`). Fixed random seeds (`random_state = 42`) make every result repeatable.

Table: Notebooks and their outputs {#tab:notebooks cols=LL}
| Notebook | Content |
|---|---|
| `00_dataset_overview` | class balance, drying years, survey dates, reported cause of drying, data-quality checks, descriptive terrain and road figures, external springs, augmentation size |
| `01_climate_features` | ERA5-Land extraction; Version A and Version B features; climate distribution figures |
| `02_model1_exploratory` | Model 1 (Version A, 29 predictors) |
| `03_model2_refined` | Model 2 (Version A, 25 predictors) |
| `04_model3_version_a` | Model 3 with the Version A window |
| `05_model3_final` | Model 3 (fixed window), comparisons, Model 3b, new-area test, PR-AUC and bootstrap CIs, lookup-table baseline, duplicate-spring check, unshuffled-CV check, leakage diagnostic |

# Corrections relative to the submitted version {#sec:appendix-corrections}

Table: Changes from the version submitted on 26 September 2026 {#tab:corrections cols=LL}
| Submitted version | This version |
|---|---|
| Climate data described as ERA5 at 0.25° (about 27 km), hourly | ERA5-Land at 0.1° (about 9 to 11 km), monthly means aggregated to years |
| Windows stated as 2009 to 2023, but the code used 2011 to 2025 | All windows end in the survey year: 2009 to 2023 for active springs and for Version B |
| Inventory of about 5,741 sources including 5,168 springs | {{facts.raw.n_records:,}} records in the survey export ({{facts.raw.n_springs:,}} springs, {{facts.raw.n_ponds}} ponds); 5,689 sources in the published description |
| Model 1 cast all predictors to integers (five features became zero) | Corrected and re-run; evaporation removal in Model 2 no longer justified by Model 1 importance |
| Model 2 had no archived code; its confusion matrix duplicated Model 1's | Model 2 re-created from its description and re-run |
| "Model 2" credited with ROC-AUC 1.0 and F1 0.99 | Those values belonged to the proposal-compliant model with the Version A window (Model 3, Version A) |
| VIF screening on all springs before the split | VIF screening fitted on training springs inside the pipeline |
| 5-fold CV in file order: F1 0.360 ± 0.106 | Shuffled stratified 5-fold CV: F1 {{m3.cv.f1_mean:.3f}} ± {{m3.cv.f1_sd:.3f}} |
| Leakage diagnostic described as perfect separation | Window end year alone: ROC-AUC {{checks.leakage_diagnostic.roc_auc:.3f}} |
| Model 3 compared with AUC 0.65 to 0.80 of Upadhyaya et al. | Those are success-rate AUCs; the prediction-rate AUC is 0.60 |
| Version A climate distributions read as "tipping points" and evaporation as "the primary driver" | Interpretations withdrawn; Version A separation is largely a window-timing artefact |
| Slope stored as sin/cos "to avoid the 0°/360° wrap-around" | Wrap-around applies to aspect; the slope variables are degenerate and not interpreted |
| Not reported | Reported cause of drying, Model 3b, input comparison, new-area test, lookup-table baseline, PR-AUC and bootstrap CIs, duplicate-spring check, external-spring cell analysis |
