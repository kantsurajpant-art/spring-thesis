"""Draw the methodology flowchart used in the report (results/figures/methodology_flowchart.png)."""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spring_drying.config import FIGURES_DIR  # noqa: E402

BOXES = {
    "data": (0.5, 0.93, 0.92, 0.09, "#dbe9f6",
             "Data collection\nICIMOD community spring inventory (7 municipalities) | ERA5-Land monthly reanalysis (0.1°)\n"
             "SRTM DEM | ICIMOD land cover | geological map | road network"),
    "prep": (0.5, 0.79, 0.92, 0.09, "#dbe9f6",
             "Pre-processing\nSpatial join to Roshi watershed -> 3,287 springs | drying year BS -> AD\n"
             "reported cause of drying matched from the raw survey | coordinate and missing-value checks"),
    "geo": (0.255, 0.615, 0.43, 0.13, "#e8f3e1",
            "Geospatial attributes (context, Models 1-2)\nelevation, aspect, slope (SRTM)\n"
            "road crossings by direction (1 km buffer)\nland cover (1 km buffer), geology"),
    "clim": (0.745, 0.615, 0.43, 0.13, "#e8f3e1",
             "Climate features (nearest 0.1° cell, 12 cells)\n15-year mean + Mann-Kendall / Sen's slope\n"
             "Version A: label-conditional window (leaky)\nVersion B: fixed 2009-2023 window"),
    "va": (0.255, 0.425, 0.43, 0.13, "#fbe3d6",
           "Version A models (leakage documented)\nModel 1: 29 features | Model 2: 25 features\n"
           "Model 3 (Version A): proposal predictors\n+ diagnostic: window end year only"),
    "vb": (0.745, 0.425, 0.43, 0.13, "#fbe3d6",
           "Version B models\nModel 3: climate + spring type (primary result)\n"
           "comparisons: spring type only, climate only\nModel 3b: drought-dried vs active (+ earthquake contrast)"),
    "rf": (0.5, 0.255, 0.92, 0.09, "#fff2cc",
           "Random Forest pipeline\nVIF screening fitted on training springs (Model 3 family) | 2,000 trees | balanced class weights\n"
           "stratified 70/30 split | random_state = 42"),
    "eval": (0.5, 0.1, 0.92, 0.1, "#eadcf2",
             "Evaluation\naccuracy, precision, recall, F1, ROC-AUC, confusion matrix | shuffled stratified 5-fold CV\n"
             "leave-one-grid-cell-out ('new area') ROC-AUC | impurity and permutation importance | lookup-table baseline"),
}
ARROWS = [("data", "prep"), ("prep", "geo"), ("prep", "clim"), ("geo", "va"), ("clim", "va"), ("clim", "vb"),
          ("va", "rf"), ("vb", "rf"), ("rf", "eval")]


def main():
    fig, ax = plt.subplots(figsize=(11, 12))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    for x, y, w, h, color, text in BOXES.values():
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.008",
                                    facecolor=color, edgecolor="black", linewidth=1.2))
        title, body = text.split("\n", 1)
        ax.text(x, y + h / 2 - 0.018, title, ha="center", va="top", fontsize=11.5, fontweight="bold")
        ax.text(x, y - 0.012, body, ha="center", va="center", fontsize=9.2, linespacing=1.35)
    for a, b in ARROWS:
        xa, ya, _, ha, *_ = BOXES[a]
        xb, yb, _, hb, *_ = BOXES[b]
        ax.add_patch(FancyArrowPatch((xa, ya - ha / 2), (xb, yb + hb / 2), arrowstyle="-|>",
                                     mutation_scale=16, linewidth=1.3, color="black", shrinkA=2, shrinkB=2))
    plt.tight_layout()
    out = FIGURES_DIR / "methodology_flowchart.png"
    plt.savefig(out, dpi=300, facecolor="white")
    print("saved", out)


if __name__ == "__main__":
    main()
