#!/usr/bin/env python3
"""
dubai_housing_export.py
───────────────────────
Fetch every *residential / apartments / house* building in Dubai **that has an
address**, enrich it with district & municipality, print each chunk to the
console, and append the chunk to one Excel sheet.

Requirements (PyPI):
    osmnx  geopandas  pandas  shapely  pyproj  openpyxl

Run:
    python -m venv venv && source venv/bin/activate
    pip install --upgrade osmnx geopandas pandas shapely pyproj openpyxl
    python dubai_housing_export.py
"""

from __future__ import annotations

import math
from pathlib import Path

import osmnx as ox
import geopandas as gpd
import pandas as pd
from shapely.geometry import box

# ─────────────────────────────── PARAMETERS ────────────────────────────────
PLACE       = "Dubai, United Arab Emirates"
GRID_N      = 6                           # 6×6 ⇒ 36 Overpass queries
OUT_XLSX    = "dubai_housing_details.xlsx"
SHEET_NAME  = "Housing"

BUILDING_TAGS = {"building": ["residential", "apartments", "house"]}
ADDR_COLS   = ["addr:housenumber", "addr:street", "addr:full"]

TARGET_COLS = [
    # IDs & basic tags
    "osmid", "name", "note",
    # address
    "addr:housenumber", "addr:street", "addr:postcode", "addr:district",
    # admin polygons
    "district", "municipality",
    # building details
    "building:levels", "levels", "height", "start_date",
    "building:material", "building:use",
]


# ─────────────────────────────── HELPERS ───────────────────────────────────
def dubai_bbox() -> tuple[float, float, float, float]:
    """Return (south, west, north, east) of Dubai admin-level 8 polygon."""
    poly = ox.features_from_place(
        PLACE, tags={"boundary": "administrative", "admin_level": "8"}
    )
    west, south, east, north = poly.union_all().bounds
    return south, west, north, east


def tile_grid(bbox: tuple[float, float, float, float], n: int):
    """Yield n×n sub-bboxes (south, west, north, east)."""
    south, west, north, east = bbox
    dlat = (north - south) / n
    dlon = (east - west) / n
    for i in range(n):
        for j in range(n):
            s, w = south + i * dlat, west + j * dlon
            yield (s, w, s + dlat, w + dlon)


def has_address(row: pd.Series) -> bool:
    """True if any address field is non-empty."""
    return any(str(row.get(col, "")).strip() for col in ADDR_COLS)


def load_admin_polygons(crs):
    """Return (districts_gdf, municipality_gdf) in the requested CRS."""
    districts = ox.features_from_place(
        PLACE,
        tags={"boundary": "administrative", "admin_level": "10"},
    )[["name", "geometry"]].rename(columns={"name": "district"}).to_crs(crs)

    municipality = ox.features_from_place(
        PLACE,
        tags={"boundary": "administrative", "admin_level": "8"},
    )[["name", "geometry"]].rename(columns={"name": "municipality"}).to_crs(crs)

    return districts, municipality


def spatial_join_admin(bldg: gpd.GeoDataFrame,
                       districts: gpd.GeoDataFrame,
                       municipality: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = gpd.sjoin(bldg, districts, predicate="within", how="left")
    out = gpd.sjoin(out, municipality, predicate="within", how="left",
                    lsuffix="", rsuffix="mun")
    # drop extra geometry columns from joins
    for col in list(out.columns):
        if col.startswith("geometry_"):
            out = out.drop(columns=col)
    return out


def ensure_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Guarantee all TARGET_COLS exist (empty str if missing)."""
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols]


# ────────────────────────────────── MAIN ───────────────────────────────────
def main() -> None:
    south, west, north, east = dubai_bbox()
    tiles = list(tile_grid((south, west, north, east), GRID_N))
    total_saved = 0
    print(f"→ Loading {len(tiles)} tiles of Dubai (grid {GRID_N}×{GRID_N})")

    # load admin polygons once
    tmp = ox.features_from_place(PLACE, tags={"boundary": "administrative",
                                              "admin_level": "10"})
    districts, municipality = load_admin_polygons(tmp.crs)

    # prepare Excel writer (overwrite if exists)
    Path(OUT_XLSX).unlink(missing_ok=True)
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl", mode="w") as writer:
        next_row = 0
        header_needed = True

        for idx, (s, w, n, e) in enumerate(tiles, 1):
            bbox_wsen = (w, s, e, n)
            try:
                gdf = ox.features_from_bbox(bbox_wsen, BUILDING_TAGS).to_crs(districts.crs)
                if gdf.empty:
                    print(f"  ! Tile {idx}/{len(tiles)} empty")
                    continue

                # keep only rows with address
                addr_mask = gdf.apply(has_address, axis=1)
                gdf = gdf[addr_mask]
                if gdf.empty:
                    print(f"  ! Tile {idx}/{len(tiles)}: no address → skipped")
                    continue

                # join admin polygons
                gdf = spatial_join_admin(gdf, districts, municipality)

                # select & order columns
                df = ensure_columns(gdf, TARGET_COLS)

                # print to console (trim wide columns)
                pd.set_option("display.max_colwidth", 35)
                print(f"\n──── Tile {idx}/{len(tiles)} — {len(df)} rows ────")
                print(df.to_string(index=False))
                print("───────────────────────────────────────────────\n")

                # append to Excel
                df.to_excel(writer, sheet_name=SHEET_NAME, index=False,
                            header=header_needed, startrow=next_row)
                next_row += len(df)
                header_needed = False
                total_saved += len(df)
                print(f"  ✓ Tile {idx}/{len(tiles)}: +{len(df)} rows saved")

            except Exception as exc:
                print(f"  ! Tile {idx}/{len(tiles)} error: {exc}")

    print(f"\n✓ Done. Saved {total_saved} rows with address → {OUT_XLSX}")


if __name__ == "__main__":
    main()
