"""ERA5-Land climate feature extraction (15-year mean + Mann-Kendall Sen's slope).

Two window designs are supported:

* Version A (label-conditional): an active spring uses the 15 years ending at the
  survey year; a dried spring uses the 15 years ending at its reported drying year.
  This design leaks the label (see notebooks/05) and is kept only to document it.
* Version B (fixed): every spring uses the same 15 years ending at the survey year.
"""
import numpy as np
import pandas as pd
import xarray as xr
from pymannkendall import original_test

from .config import ERA5_LAND_FIRST_YEAR, NC_PATH, WINDOW_END, WINDOW_LEN

VAR_MAP = {"Dewpoint": "d2m", "Temperature": "t2m", "Precipitation": "tp", "Evaporation": "pev"}
FEATURE_COLS = [f"{label}_{kind}" for kind in ("rate", "mean") for label in VAR_MAP]


def to_annual(ds: xr.Dataset) -> xr.Dataset:
    """Monthly ERA5-Land means -> annual values in physical units.

    tp and pev are monthly means of daily accumulations (m/day): converted to mm/year.
    pev keeps the ECMWF sign convention (negative = evaporation), so it is negated
    to give a positive potential-evaporation depth.
    """
    ann = ds.resample(valid_time="YE").mean()
    ann["tp"] = ann["tp"] * 1000 * 365
    ann["pev"] = -ann["pev"] * 1000 * 365
    ann["d2m"] = ann["d2m"] - 273.15
    ann["t2m"] = ann["t2m"] - 273.15
    return ann


def _nearest_index(grid, values):
    return np.abs(np.asarray(grid)[None, :] - np.asarray(values)[:, None]).argmin(1)


def grid_cell_ids(lat, lon, nc_path=NC_PATH) -> np.ndarray:
    """Index of the nearest climate grid cell for every spring (for spatial CV groups)."""
    with xr.open_dataset(nc_path) as ds:
        la, lo = ds.latitude.values, ds.longitude.values
    return _nearest_index(la, lat) * len(lo) + _nearest_index(lo, lon)


def cell_annual_series(lat, lon, nc_path=NC_PATH):
    """Annual climate series for every distinct grid cell used by the springs.

    Returns (annual DataFrame indexed by (cell, year), cell id per spring). Only the
    few distinct cells are read from disk, so this is fast even for the full record.
    """
    with xr.open_dataset(nc_path) as ds:
        ila, ilo = _nearest_index(ds.latitude.values, lat), _nearest_index(ds.longitude.values, lon)
        cells = ila * ds.sizes["longitude"] + ilo
        uniq, first = np.unique(cells, return_index=True)
        pts = ds.isel(latitude=xr.DataArray(ila[first], dims="cell"),
                      longitude=xr.DataArray(ilo[first], dims="cell")).load().astype("float64")
        last = pd.Timestamp(ds.valid_time.values[-1])
    ann = to_annual(pts)
    years = ann["valid_time"].dt.year.values
    # keep complete calendar years only (the record ends in April 2026)
    complete = years <= (last.year if last.month == 12 else last.year - 1)
    frames = []
    for i, cell in enumerate(uniq):
        df = pd.DataFrame({v: ann[v].isel(cell=i).values[complete] for v in VAR_MAP.values()},
                          index=pd.Index(years[complete], name="year"))
        df["cell"] = cell
        frames.append(df.reset_index())
    return pd.concat(frames).set_index(["cell", "year"]).sort_index(), cells


def window_features(annual: pd.DataFrame, cells, end_years, length=WINDOW_LEN) -> pd.DataFrame:
    """Mean and Sen's slope over (end-length, end] for each spring.

    Rows whose window would start before the first ERA5-Land year, or whose end year
    is missing, get NaN (no complete window exists)."""
    cache = {}
    rows = []
    for cell, end in zip(cells, end_years):
        if pd.isna(end) or end - length + 1 < ERA5_LAND_FIRST_YEAR:
            rows.append({c: np.nan for c in FEATURE_COLS})
            continue
        key = (int(cell), int(end))
        if key not in cache:
            win = annual.loc[cell].loc[int(end) - length + 1:int(end)]
            if len(win) != length:
                raise ValueError(f"incomplete window for cell {cell} ending {end}: {len(win)} years")
            rec = {}
            for label, var in VAR_MAP.items():
                rec[f"{label}_rate"] = float(original_test(win[var].values).slope)
                rec[f"{label}_mean"] = float(win[var].mean())
            cache[key] = rec
        rows.append(cache[key])
    return pd.DataFrame(rows, columns=FEATURE_COLS)


def fixed_window_features(lat, lon, end=WINDOW_END, length=WINDOW_LEN, nc_path=NC_PATH) -> pd.DataFrame:
    """Version B: the same calendar window (end-length, end] for every spring."""
    annual, cells = cell_annual_series(lat, lon, nc_path)
    return window_features(annual, cells, np.full(len(cells), end), length)


def label_conditional_features(lat, lon, dried, dried_year, survey_year=WINDOW_END,
                               length=WINDOW_LEN, nc_path=NC_PATH) -> pd.DataFrame:
    """Version A: active springs end at the survey year, dried springs at their drying year.
    Dried springs without a reported year get NaN (their window is undefined)."""
    annual, cells = cell_annual_series(lat, lon, nc_path)
    end_years = np.where(np.asarray(dried) == 1, np.asarray(dried_year, dtype=float), survey_year)
    return window_features(annual, cells, end_years, length)
