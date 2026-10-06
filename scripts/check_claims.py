"""Check that every number quoted from the literature in report/src/report.md
appears in the abstract of the cited paper (report/src/abstracts.json).

Output: report/claims_check.csv (claim, reference, phrase searched, found yes/no).
Usage (from the repo root):  python scripts/check_claims.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "report" / "src"

# (reference key, claim as written in the report, phrase that must occur in the abstract)
CLAIMS = [
    ("adhikari2021", "more than 4,222 springs across five watersheds", "4,222 springs"),
    ("adhikari2021", "discharge of about 70% decreasing", "about 70% were decreasing"),
    ("pandit2024", "73% of 1,122 springs declining", "73% of the springs"),
    ("pandit2024", "1,122 springs mapped", "1122 springs"),
    ("pandit2024", "2% already dried", "2% already dried"),
    ("pandit2024", "increase in temperature and localised high-intensity rainfall", "localised high-intensity rainfall"),
    ("chauhan2023", "about 16% of springs dried", "16% had already dried"),
    ("chauhan2023", "about 60% declining discharge", "about 60% have declining discharge"),
    ("pandit2026", "5,689 water sources", "5689 water sources"),
    ("pandit2026", "5,168 springs and 521 ponds", "5168 springs and 521 ponds"),
    ("pandit2026", "27% of sources dried", "27 % of documented sources have dried"),
    ("pandit2026", "drying due to earthquakes, droughts and infrastructure", "earthquakes, droughts, and infrastructure development"),
    ("poudel2017", "73.2% decreased flow", "73.2%"),
    ("poudel2017", "12.2% dried", "12.2% had dried up"),
    ("tambe2012", "lean-period discharge declined by nearly 50% in drought-prone areas", "nearly 50% in drought-prone areas"),
    ("tambe2012", "rise in rainfall intensity, reduction in temporal spread, decline in winter rain", "decline in winter rain"),
    ("chapagain2019", "immediate drying effect in about 18% of springs (2015 earthquake)", "immediate drying effect in about 18%"),
    ("chapagain2019", "water volume of about 30% of springs decreased", "about 30% of the springs has decreased"),
    ("thapa2023", "300 local government units", "300 local government units"),
    ("thapa2023", "springs dried in 74% of units", "74% of local government units"),
    ("thapa2023", "roads/infrastructure main cause, then earthquakes and climate change", "Road and infrastructure construction is the main cause of springs drying up, followed by earthquakes and climate change"),
    ("niraula2021", "621 spring and 815 non-spring locations", "815 non-spring locations"),
    ("niraula2021", "92% accuracy (Bootstrap Forest)", "92% accuracy"),
    ("niraula2021", "75% on an independent dataset", "75% accuracy"),
    ("alshabeeb2023", "RF ROC-AUC 0.748", "AUROCC = 0.748"),
    ("alshabeeb2023", "SVM 0.732, MARS 0.727, BRT 0.689", "AUROCC SVM = 0.732, AUROCC MARS = 0.727, and AUROCC BRT = 0.689"),
    ("alshabeeb2023", "200 springs, 13 predictors", "200 spring locations and 13 predictor variables"),
    ("guo2023", "RF AUC 0.757 without climate factors", "AUC: 0.757"),
    ("guo2023", "climate factors raised RF AUC by 0.073", "AUC + 0.073"),
    ("upadhyaya2024", "success-rate AUC 0.80 (MFR)", "AUC of 0.80"),
    ("upadhyaya2024", "success-rate AUC 0.65 (FR)", "AUC of 0.65"),
    ("upadhyaya2024", "prediction-rate AUC 0.60 for both", "AUC of 0.60 for the prediction rate curve"),
    ("ishikawa2025", "228 springs; 192 discharging, 44 depleted", "depleted: 44, discharging: 192"),
    ("ishikawa2025", "ROC-AUC 0.84 (LR), 0.86 (RF), 0.84 (SVM)", "0.84 (LR), 0.86 (RF), and 0.84 (SVM)"),
    ("ishikawa2025", "precision-recall AUC also reported", "AUC-PR"),
    ("kapoor2023", "leakage in 17 fields affecting 294 papers", "17 fields where leakage has been found, collectively affecting 294 papers"),
    ("koldasbayeva2025", "random CV overestimates AUC by up to 0.16", "overestimates AUC by up to 0.16"),
    ("munozsabater2021", "ERA5-Land resolution about 9 km", "9 km"),
    ("khadka2022", "air temperature best captured", "Air temperature is the variable that is best captured"),
    ("khadka2022", "monsoon precipitation strongly overestimated", "spectacular overestimation of precipitation during the monsoon"),
    ("lavers2022", "general wet bias in ERA5 precipitation", "ERA5 wet bias"),
    ("santos2018", "oversampling before CV gives over-optimistic estimates", "overly-optimistic estimates"),
    ("wenger2012", "good in-sample performance does not guarantee transferability", "poor transferability"),
    ("thapa2025", "collected by trained community resource persons with Survey123; public via ICIMOD RDS", "Regional Database System"),
]


def main():
    abstracts = json.loads((SRC / "abstracts.json").read_text(encoding="utf-8-sig"))
    report = (SRC / "report.md").read_text(encoding="utf-8-sig")
    rows, failed = [], 0
    for key, claim, phrase in CLAIMS:
        abstract = abstracts.get(key, "")
        found = phrase.lower() in abstract.lower()
        cited = f"@{key}" in report
        failed += (not found) or (not cited)
        rows.append({"reference": key, "claim_in_report": claim, "phrase_searched": phrase,
                     "found_in_abstract": "yes" if found else "NO", "cited_in_report": "yes" if cited else "NO"})
    with open(ROOT / "report" / "claims_check.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"{len(rows) - failed} of {len(rows)} literature claims verified against abstracts")
    for r in rows:
        if r["found_in_abstract"] == "NO" or r["cited_in_report"] == "NO":
            print("  FAILED:", r)


if __name__ == "__main__":
    main()
