# Input data (not tracked in git)

| File | Size | What it is |
|---|---|---|
| `baf400466b67369cecb11d5d456ba48c.nc` | ~745 MB | ERA5-Land monthly means, 0.1° grid, 1950-01 → 2026-04, 0–40°N / 60–100°E. Variables: `d2m`, `t2m` (K), `tp`, `pev` (m/day, ECMWF sign: negative = evaporation). Downloaded from the Copernicus CDS. |
| `Full_Analysis_data.csv` | ~19 MB | Master spring table (3,287 springs): field survey attributes, DEM / aspect / slope, road counts, geology, LULC, and the **label-conditional** climate columns. |

Currently these live in `../Project Preperation Rough/` (a second copy of the CSV is in `../9-credit Project/`).

`src/spring_drying/config.py` finds them automatically in this order:

1. `SPRING_DATA_DIR` environment variable
2. this `data/` folder
3. `../Project Preperation Rough/`

Do not edit `Full_Analysis_data.csv` in place: treat it as raw, read-only input.
