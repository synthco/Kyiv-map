"""
build_tile_sources.py
Export GeoJSON source files for tippecanoe tile generation.

Outputs (all in build/tile-sources/):
  transportation.geojson  — roads (source-layer: transportation)
  aeroway.geojson         — runways/taxiways (source-layer: aeroway)
  buildings.geojson       — building footprints, id only (source-layer: building)
  building_depth.geojson  — building footprints + foundationDepth (source-layer: building_depth)
  water.geojson           — water bodies from OSM PBF (source-layer: water)
"""

from __future__ import annotations

import gzip
import json
import shutil
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
GENERATED_DIR = ROOT / "generated" / "city-data"
BUILD_DIR = ROOT / "build"
OSM_DIR = ROOT / "data-src" / "osm"
OUT_DIR = BUILD_DIR / "tile-sources"

ROADS_GZ = GENERATED_DIR / "roads.geojson.gz"
RUNWAYS_GZ = GENERATED_DIR / "runways_taxiways.geojson.gz"
BUILDINGS_PARQUET = BUILD_DIR / "buildings.normalized.parquet"

# KYV bounding box [minLon, minLat, maxLon, maxLat]
BBOX = (30.095930481829672, 50.24450228086875, 31.03257386656265, 50.6325759924907)
BBOX_BOX = box(BBOX[0], BBOX[1], BBOX[2], BBOX[3])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def log(msg: str) -> None:
    print(f"[build_tile_sources] {msg}", flush=True)


def load_geojson_gz(path: Path) -> dict:
    log(f"Decompressing {path.name} ...")
    with gzip.open(path, "rb") as f:
        return json.loads(f.read())


def write_geojson(data: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, separators=(",", ":")))
    size_kb = out_path.stat().st_size // 1024
    log(f"  → {out_path.relative_to(ROOT)} ({size_kb} KB, {len(data.get('features', []))} features)")


# ---------------------------------------------------------------------------
# Roads → transportation.geojson
# ---------------------------------------------------------------------------


def export_roads() -> None:
    log("Exporting roads → transportation.geojson ...")
    fc = load_geojson_gz(ROADS_GZ)
    # Property names already match game schema (roadClass, structure, name, id)
    write_geojson(fc, OUT_DIR / "transportation.geojson")


# ---------------------------------------------------------------------------
# Runways → aeroway.geojson
# ---------------------------------------------------------------------------


def export_aeroways() -> None:
    log("Exporting runways/taxiways → aeroway.geojson ...")
    fc = load_geojson_gz(RUNWAYS_GZ)
    write_geojson(fc, OUT_DIR / "aeroway.geojson")


# ---------------------------------------------------------------------------
# Buildings parquet → buildings.geojson + building_depth.geojson
# ---------------------------------------------------------------------------


def export_buildings() -> None:
    log("Exporting buildings from parquet ...")
    gdf = gpd.read_parquet(BUILDINGS_PARQUET)
    log(f"  Read {len(gdf)} buildings from parquet.")

    # Clip to bbox
    gdf = gdf[gdf.geometry.intersects(BBOX_BOX)].copy()
    log(f"  {len(gdf)} buildings within KYV bbox.")

    # ---- buildings.geojson (main tiles: only id + geometry) ----
    buildings_gdf = gdf[["id", "geometry"]].copy()
    buildings_fc = json.loads(buildings_gdf.to_json())
    write_geojson(buildings_fc, OUT_DIR / "buildings.geojson")

    # ---- building_depth.geojson (foundation tiles: foundationDepth + geometry) ----
    depth_cols = ["id", "geometry"]
    if "foundationDepth" in gdf.columns:
        depth_cols.append("foundationDepth")
    depth_gdf = gdf[depth_cols].copy()
    depth_fc = json.loads(depth_gdf.to_json())
    write_geojson(depth_fc, OUT_DIR / "building_depth.geojson")


# ---------------------------------------------------------------------------
# Water from OSM PBF → water.geojson
# ---------------------------------------------------------------------------


def _find_osm_pbf() -> Path:
    if not OSM_DIR.exists():
        return None
    candidates = sorted(OSM_DIR.glob("*.osm.pbf"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def export_water() -> None:
    osm_pbf = _find_osm_pbf()
    if osm_pbf is None:
        log("WARNING: No OSM PBF found, skipping water extraction.")
        # Write empty FeatureCollection so tippecanoe doesn't fail
        write_geojson({"type": "FeatureCollection", "features": []}, OUT_DIR / "water.geojson")
        return

    log(f"Extracting water from {osm_pbf.name} ...")

    if not shutil.which("osmium"):
        log("WARNING: osmium not found on PATH, skipping water extraction.")
        write_geojson({"type": "FeatureCollection", "features": []}, OUT_DIR / "water.geojson")
        return

    filtered_pbf = BUILD_DIR / "kyv-water.osm.pbf"
    water_geojson_raw = BUILD_DIR / "kyv-water-raw.geojson"
    water_geojson_out = OUT_DIR / "water.geojson"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Filter OSM features for water tags
    subprocess.run(
        [
            "osmium", "tags-filter",
            str(osm_pbf),
            "nw/natural=water",
            "nw/waterway=river,stream,canal,drain,ditch",
            "a/natural=water",
            "a/landuse=reservoir",
            "-o", str(filtered_pbf),
            "--overwrite",
        ],
        check=True,
    )
    log(f"  Filtered water PBF → {filtered_pbf.name}")

    # Export to GeoJSON (osmium export handles geometry)
    subprocess.run(
        [
            "osmium", "export",
            str(filtered_pbf),
            "--geometry-types=polygon,linestring",
            "--output-format=geojson",
            "-o", str(water_geojson_raw),
            "--overwrite",
        ],
        check=True,
    )
    log(f"  Exported raw water GeoJSON → {water_geojson_raw.name}")

    # Clip to KYV bbox and simplify properties
    water_gdf = gpd.read_file(water_geojson_raw)
    if len(water_gdf) == 0:
        log("  No water features found.")
        write_geojson({"type": "FeatureCollection", "features": []}, water_geojson_out)
        return

    water_gdf = water_gdf.clip(BBOX_BOX)
    # Keep only useful properties
    keep_cols = [c for c in ["natural", "waterway", "name", "geometry"] if c in water_gdf.columns]
    water_gdf = water_gdf[keep_cols].copy()
    water_fc = json.loads(water_gdf.to_json())
    write_geojson(water_fc, water_geojson_out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Output directory: {OUT_DIR.relative_to(ROOT)}")

    export_roads()
    export_aeroways()
    export_buildings()
    export_water()

    log("All tile sources exported successfully.")


if __name__ == "__main__":
    main()
