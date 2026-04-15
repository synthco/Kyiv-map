from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_SRC_DIR = ROOT_DIR / "data-src"
OSM_DIR = DATA_SRC_DIR / "osm"
OPEN_DATA_DIR = DATA_SRC_DIR / "open-data"
BUILD_DIR = ROOT_DIR / "build"
VALIDATION_DIR = BUILD_DIR / "validation"
GENERATED_DIR = ROOT_DIR / "generated"
CITY_DATA_DIR = GENERATED_DIR / "city-data"

BBOX = (
    30.095930481829672,
    50.24450228086875,
    31.03257386656265,
    50.6325759924907,
)

OSRM_BASE_URL = os.environ.get("KYV_OSRM_BASE_URL", "http://127.0.0.1:5000")
DEFAULT_FOUNDATION_DEPTH = float(os.environ.get("KYV_DEFAULT_FOUNDATION_DEPTH", "-5"))
BUILDING_GRID_CELL_SIZE = float(os.environ.get("KYV_BUILDING_GRID_CELL_SIZE", "0.005"))

SOURCE_MANIFEST_PATH = DATA_SRC_DIR / "sources_manifest.json"
BBOX_MANIFEST_PATH = VALIDATION_DIR / "bbox_manifest.json"
VALIDATION_REPORT_PATH = VALIDATION_DIR / "city_data_validation.json"

OSM_PBF_PATH = OSM_DIR / "ukraine-latest.osm.pbf"
WORLDPOP_RASTER_PATH = OPEN_DATA_DIR / "worldpop_ukr_2025_100m.tif"
DEMAND_SEED_PATH = OPEN_DATA_DIR / "demand_seed.csv"

ROADS_NORMALIZED_PATH = BUILD_DIR / "roads.normalized.parquet"
RUNWAYS_NORMALIZED_PATH = BUILD_DIR / "runways_taxiways.normalized.parquet"
BUILDINGS_NORMALIZED_PATH = BUILD_DIR / "buildings.normalized.parquet"
DEMAND_POINTS_PATH = BUILD_DIR / "demand_points.parquet"
DEMAND_ROUTE_CACHE_PATH = BUILD_DIR / "demand_route_cache.json"

ROADS_OUTPUT_PATH = CITY_DATA_DIR / "roads.geojson.gz"
RUNWAYS_OUTPUT_PATH = CITY_DATA_DIR / "runways_taxiways.geojson.gz"
BUILDINGS_INDEX_OUTPUT_PATH = CITY_DATA_DIR / "buildings_index.json.gz"
DEMAND_DATA_OUTPUT_PATH = CITY_DATA_DIR / "demand_data.json.gz"

DEMAND_GRID_CELL_SIZE_M = float(os.environ.get("KYV_DEMAND_GRID_CELL_SIZE_M", "700"))
DEMAND_COMMUTE_SHARE = float(os.environ.get("KYV_DEMAND_COMMUTE_SHARE", "0.42"))
TARGET_JOBS_SHARE = float(os.environ.get("KYV_TARGET_JOBS_SHARE", "0.45"))
AIRPORT_MINIMUM_JOBS = int(os.environ.get("KYV_AIRPORT_MINIMUM_JOBS", "15000"))
AIRPORT_MINIMUM_CELL_JOBS = int(os.environ.get("KYV_AIRPORT_MINIMUM_CELL_JOBS", "250"))
TOP_JOBS_MINIMUM_CELL_JOBS = int(os.environ.get("KYV_TOP_JOBS_MINIMUM_CELL_JOBS", "50"))
ROAD_SNAP_RADIUS_M = float(os.environ.get("KYV_ROAD_SNAP_RADIUS_M", "1500"))
EMPLOYMENT_HUB_MIN_JOBS = int(os.environ.get("KYV_EMPLOYMENT_HUB_MIN_JOBS", "150"))
EMPLOYMENT_HUB_TOP_PERCENTILE = float(os.environ.get("KYV_EMPLOYMENT_HUB_TOP_PERCENTILE", "0.08"))
COMMUTE_PRIMARY_MAX_DISTANCE_KM = float(os.environ.get("KYV_COMMUTE_PRIMARY_MAX_DISTANCE_KM", "40"))

ROAD_CLASS_VOCAB = (
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "residential",
    "service",
    "living_street",
    "unclassified",
    "link",
    "other",
)

STRUCTURE_VOCAB = ("ground", "bridge", "tunnel", "ford", "other")

SOURCE_SPECS = {
    "osm_ukraine_pbf": {
        "url": "https://download.geofabrik.de/europe/ukraine-latest.osm.pbf",
        "path": OSM_PBF_PATH,
        "required": True,
        "mode": "download",
        "description": "Bulk OSM extract for Ukraine used as the primary geometry source.",
    },
    "worldpop_ukr_2025_100m": {
        "url": "https://hub.worldpop.org/geodata/summary?id=52378",
        "path": WORLDPOP_RASTER_PATH,
        "required": True,
        "mode": "manual",
        "description": "WorldPop Ukraine 2025 population counts raster used to derive residents per demand cell.",
    },
    "demand_seed_csv": {
        "url": None,
        "path": DEMAND_SEED_PATH,
        "required": False,
        "mode": "manual",
        "description": "Generated clustered demand seed with jobs/residents per cell.",
    },
}


def resolve_osm_pbf_path() -> Path:
    if OSM_PBF_PATH.exists():
        return OSM_PBF_PATH

    candidates = sorted(OSM_DIR.glob("*.osm.pbf"), key=lambda path: path.stat().st_mtime, reverse=True)
    if candidates:
        return candidates[0]

    return OSM_PBF_PATH
