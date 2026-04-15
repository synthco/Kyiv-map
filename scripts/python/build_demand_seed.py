from __future__ import annotations

import argparse
import math
from pathlib import Path

from config import (
    AIRPORT_MINIMUM_CELL_JOBS,
    AIRPORT_MINIMUM_JOBS,
    BBOX,
    BUILDINGS_NORMALIZED_PATH,
    DEMAND_GRID_CELL_SIZE_M,
    DEMAND_SEED_PATH,
    ROAD_SNAP_RADIUS_M,
    ROADS_NORMALIZED_PATH,
    TARGET_JOBS_SHARE,
    TOP_JOBS_MINIMUM_CELL_JOBS,
    WORLDPOP_RASTER_PATH,
    resolve_osm_pbf_path,
)
from common import ensure_directories, import_dependency
from osm_reader import load_aerodrome_features, load_building_features, load_landuse_features, load_poi_features


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate demand_seed.csv from WorldPop residents and OSM-inferred jobs for the KYV extent."
    )
    parser.add_argument("--worldpop", type=Path, default=WORLDPOP_RASTER_PATH, help="Path to the WorldPop GeoTIFF.")
    parser.add_argument("--output", type=Path, default=DEMAND_SEED_PATH, help="Output CSV path.")
    return parser.parse_args()


def create_grid(cell_size_m: float):
    gpd = import_dependency("geopandas")
    shapely_geometry = import_dependency("shapely.geometry", "shapely")

    bbox_geom = gpd.GeoDataFrame({"geometry": [shapely_geometry.box(*BBOX)]}, crs="EPSG:4326").to_crs("EPSG:3857")
    bbox_shape = bbox_geom.geometry.iloc[0]
    minx, miny, maxx, maxy = bbox_shape.bounds

    cols = int(math.ceil((maxx - minx) / cell_size_m))
    rows = int(math.ceil((maxy - miny) / cell_size_m))
    records: list[dict] = []

    for col in range(cols):
        x0 = minx + (col * cell_size_m)
        x1 = min(x0 + cell_size_m, maxx)
        for row in range(rows):
            y0 = miny + (row * cell_size_m)
            y1 = min(y0 + cell_size_m, maxy)
            cell_geom = shapely_geometry.box(x0, y0, x1, y1).intersection(bbox_shape)
            if cell_geom.is_empty:
                continue
            records.append(
                {
                    "id": f"cell-{col}-{row}",
                    "col": col,
                    "row": row,
                    "geometry": cell_geom,
                }
            )

    grid = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:3857")
    grid["jobs_raw"] = 0.0
    grid["residents_raw"] = 0.0
    grid["building_jobs"] = 0.0
    grid["poi_jobs"] = 0.0
    grid["landuse_jobs"] = 0.0
    grid["airport_bonus"] = 0.0
    grid["airport_weight"] = 0.0
    return grid, (minx, miny, maxx, maxy)


def cell_id_for_xy(x: float, y: float, grid_bounds: tuple[float, float, float, float], cell_size_m: float) -> tuple[int, int]:
    minx, miny, maxx, maxy = grid_bounds
    col = int((min(max(x, minx), maxx - 1e-6) - minx) // cell_size_m)
    row = int((min(max(y, miny), maxy - 1e-6) - miny) // cell_size_m)
    return col, row


def load_worldpop_residents(worldpop_path: Path, grid, grid_bounds: tuple[float, float, float, float], cell_size_m: float) -> None:
    numpy = import_dependency("numpy")
    pandas = import_dependency("pandas")
    rasterio = import_dependency("rasterio")
    rasterio_windows = import_dependency("rasterio.windows", "rasterio")

    if not worldpop_path.exists():
        raise SystemExit(f"Missing WorldPop raster: {worldpop_path}")

    with rasterio.open(worldpop_path) as src:
        if str(src.crs).upper() not in {"EPSG:4326", "OGC:CRS84"}:
            raise SystemExit(f"WorldPop raster must be in EPSG:4326, got {src.crs}")

        window = rasterio_windows.from_bounds(*BBOX, transform=src.transform)
        data = src.read(1, window=window, masked=True)
        transform = src.window_transform(window)
        valid = (~numpy.ma.getmaskarray(data)) & numpy.isfinite(data) & (data > 0)
        rows, cols = numpy.where(valid)
        if len(rows) == 0:
            raise SystemExit("WorldPop raster returned no positive population pixels inside the KYV bbox.")

        xs, ys = rasterio.transform.xy(transform, rows, cols, offset="center")
        pixels = pandas.DataFrame(
            {
                "lon": xs,
                "lat": ys,
                "population": data.data[rows, cols].astype(float),
            }
        )

    gpd = import_dependency("geopandas")
    pixels_gdf = gpd.GeoDataFrame(
        pixels,
        geometry=gpd.points_from_xy(pixels["lon"], pixels["lat"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:3857")

    pixels_gdf["col"], pixels_gdf["row"] = zip(
        *pixels_gdf.geometry.apply(lambda geom: cell_id_for_xy(geom.x, geom.y, grid_bounds, cell_size_m))
    )
    residents = pixels_gdf.groupby(["col", "row"])["population"].sum().rename("residents_raw")
    grid_index = grid.set_index(["col", "row"])
    grid_index.loc[residents.index, "residents_raw"] = residents
    grid[["residents_raw"]] = grid_index[["residents_raw"]].reset_index(drop=True)


def parse_levels(value: str, default_levels: int) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return default_levels
    return min(60, max(1, parsed))


def classify_building(row) -> tuple[str | None, int, float]:
    building = str(row.building or "").strip().lower()
    office = str(getattr(row, "office", "") or "").strip().lower()
    shop = str(getattr(row, "shop", "") or "").strip().lower()
    amenity = str(getattr(row, "amenity", "") or "").strip().lower()
    tourism = str(getattr(row, "tourism", "") or "").strip().lower()
    railway = str(getattr(row, "railway", "") or "").strip().lower()
    public_transport = str(getattr(row, "public_transport", "") or "").strip().lower()
    aeroway = str(getattr(row, "aeroway", "") or "").strip().lower()
    government = str(getattr(row, "government", "") or "").strip().lower()

    if aeroway == "terminal" or building == "terminal":
        return "airport_terminal", 2, 30.0
    if office or building == "office":
        return "office", 4, 25.0
    if amenity == "hospital":
        return "hospital", 3, 30.0
    if amenity == "clinic":
        return "clinic", 3, 30.0
    if amenity == "school":
        return "school", 3, 40.0
    if amenity == "college":
        return "college", 3, 40.0
    if amenity == "university":
        return "university", 4, 40.0
    if shop or building in {"retail", "supermarket", "kiosk", "mall"}:
        return "retail", 2, 35.0
    if building == "commercial":
        return "commercial", 3, 30.0
    if government or building in {"public", "government", "civic", "administrative"} or amenity in {
        "courthouse",
        "townhall",
        "post_office",
        "police",
        "fire_station",
    }:
        return "public", 3, 35.0
    if building in {"industrial", "factory", "manufacture"}:
        return "industrial", 1, 80.0
    if building == "warehouse":
        return "warehouse", 1, 120.0
    if tourism == "hotel" or building == "hotel":
        return "hotel", 5, 50.0
    if public_transport or railway == "station" or building in {"train_station", "transportation"}:
        return "transport", 2, 40.0

    return None, 1, 0.0


def classify_poi_job_weight(row) -> float:
    office = str(row.office or "").strip().lower()
    shop = str(row.shop or "").strip().lower()
    amenity = str(row.amenity or "").strip().lower()
    railway = str(row.railway or "").strip().lower()
    public_transport = str(row.public_transport or "").strip().lower()
    tourism = str(row.tourism or "").strip().lower()

    if office:
        return 40.0
    if amenity == "bank":
        return 20.0
    if amenity == "hospital":
        return 400.0
    if amenity == "clinic":
        return 80.0
    if amenity == "university":
        return 1200.0
    if amenity == "college":
        return 350.0
    if amenity == "school":
        return 120.0
    if amenity == "kindergarten":
        return 35.0
    if railway == "station" or public_transport == "station" or amenity in {"bus_station", "ferry_terminal"}:
        return 120.0
    if amenity in {"courthouse", "townhall", "post_office", "police", "fire_station"}:
        return 90.0
    if tourism == "hotel":
        return 80.0
    if shop == "mall":
        return 400.0
    if shop == "supermarket":
        return 60.0
    if shop:
        return 12.0
    return 0.0


def load_building_jobs(grid, grid_bounds: tuple[float, float, float, float], cell_size_m: float):
    gpd = import_dependency("geopandas")
    required_columns = {
        "source_osm_id",
        "building",
        "building_levels",
        "office",
        "shop",
        "amenity",
        "tourism",
        "railway",
        "public_transport",
        "aeroway",
        "government",
        "geometry",
    }
    if BUILDINGS_NORMALIZED_PATH.exists():
        buildings = gpd.read_parquet(BUILDINGS_NORMALIZED_PATH)
        if required_columns - set(buildings.columns):
            buildings = load_building_features()
    else:
        buildings = load_building_features()

    buildings = buildings.to_crs("EPSG:3857")
    jobs_rows: list[dict] = []

    for row in buildings.itertuples():
        category, default_levels, divisor = classify_building(row)
        if category is None:
            continue

        levels = parse_levels(getattr(row, "building_levels", ""), default_levels)
        area_m2 = float(row.geometry.area)
        if area_m2 <= 0:
            continue

        jobs = (area_m2 * levels) / divisor
        centroid = row.geometry.centroid
        col, row_idx = cell_id_for_xy(centroid.x, centroid.y, grid_bounds, cell_size_m)
        jobs_rows.append(
            {
                "source_osm_id": row.source_osm_id,
                "category": category,
                "jobs": jobs,
                "col": col,
                "row": row_idx,
                "geometry": row.geometry,
            }
        )

    jobs_gdf = gpd.GeoDataFrame(jobs_rows, geometry="geometry", crs="EPSG:3857")
    if jobs_gdf.empty:
        raise SystemExit("No employment-related buildings were derived from OSM.")

    grouped = jobs_gdf.groupby(["col", "row"])["jobs"].sum()
    airport_weights = jobs_gdf[jobs_gdf["category"].isin({"airport_terminal", "transport"})].groupby(["col", "row"])["jobs"].sum()
    grid_index = grid.set_index(["col", "row"])
    grid_index.loc[grouped.index, "building_jobs"] = grouped
    if not airport_weights.empty:
        grid_index.loc[airport_weights.index, "airport_weight"] = airport_weights
    grid[["building_jobs", "airport_weight"]] = grid_index[["building_jobs", "airport_weight"]].reset_index(drop=True)

    return jobs_gdf


def load_poi_jobs(grid, grid_bounds: tuple[float, float, float, float], cell_size_m: float, employment_buildings):
    gpd = import_dependency("geopandas")

    pois = load_poi_features().to_crs("EPSG:3857")
    if pois.empty:
        return

    if not employment_buildings.empty:
        building_shapes = employment_buildings[["geometry"]].copy()
        joined = gpd.sjoin(pois, building_shapes, how="left", predicate="within")
        pois = joined[joined["index_right"].isna()].drop(columns=["index_right"])

    if pois.empty:
        return

    pois["poi_jobs"] = pois.apply(classify_poi_job_weight, axis=1)
    pois = pois[pois["poi_jobs"] > 0].copy()
    if pois.empty:
        return

    pois["col"], pois["row"] = zip(
        *pois.geometry.apply(lambda geom: cell_id_for_xy(geom.x, geom.y, grid_bounds, cell_size_m))
    )
    grouped = pois.groupby(["col", "row"])["poi_jobs"].sum()
    grid_index = grid.set_index(["col", "row"])
    grid_index.loc[grouped.index, "poi_jobs"] = grouped
    grid[["poi_jobs"]] = grid_index[["poi_jobs"]].reset_index(drop=True)


def load_landuse_jobs(grid, employment_buildings):
    numpy = import_dependency("numpy")
    shapely = import_dependency("shapely")

    density_by_landuse = {
        "industrial": 25.0,
        "commercial": 45.0,
        "retail": 60.0,
        "railway": 15.0,
        "port": 20.0,
        "construction": 5.0,
    }
    landuse = load_landuse_features().to_crs("EPSG:3857")
    if landuse.empty:
        return

    employment_geoms = numpy.array(list(employment_buildings.geometry), dtype=object)
    building_tree = shapely.STRtree(employment_geoms) if len(employment_geoms) else None
    cell_geoms = numpy.array(list(grid.geometry), dtype=object)
    cell_tree = shapely.STRtree(cell_geoms)

    for row in landuse.itertuples():
        density = density_by_landuse.get(str(row.landuse))
        if density is None:
            continue

        geom = row.geometry
        if geom.is_empty or geom.area <= 0:
            continue

        if building_tree is not None:
            building_indices = building_tree.query(geom, predicate="intersects")
            if len(building_indices):
                overlap_union = shapely.union_all(employment_geoms.take(building_indices))
                geom = geom.difference(overlap_union)
                if geom.is_empty or geom.area <= 0:
                    continue

        cell_indices = cell_tree.query(geom, predicate="intersects")
        for cell_idx in cell_indices:
            overlap_area = geom.intersection(cell_geoms[cell_idx]).area
            if overlap_area <= 0:
                continue
            grid.at[int(cell_idx), "landuse_jobs"] += density * (overlap_area / 10000.0)


def pick_boryspil_aerodrome():
    gpd = import_dependency("geopandas")
    shapely_geometry = import_dependency("shapely.geometry", "shapely")

    aerodromes = load_aerodrome_features()
    if aerodromes.empty:
        return None

    exact = aerodromes[
        aerodromes["iata"].str.upper().eq("KBP")
        | aerodromes["icao"].str.upper().eq("UKBB")
        | aerodromes["name"].str.contains("борисп|borysp", case=False, regex=True)
    ]
    if not exact.empty:
        return exact.iloc[0]

    reference = gpd.GeoSeries([shapely_geometry.Point(30.894, 50.345)], crs="EPSG:4326").to_crs("EPSG:3857").iloc[0]
    projected = aerodromes.to_crs("EPSG:3857")
    projected["distance"] = projected.geometry.centroid.distance(reference)
    nearest_idx = projected["distance"].idxmin()
    return aerodromes.loc[nearest_idx]


def apply_airport_bonus(grid):
    gpd = import_dependency("geopandas")

    aerodrome_row = pick_boryspil_aerodrome()
    if aerodrome_row is None:
        return

    airport_area = gpd.GeoSeries([aerodrome_row.geometry], crs="EPSG:4326").to_crs("EPSG:3857").iloc[0].buffer(1500)
    airport_cell_indexes = grid[grid.geometry.intersects(airport_area)].index
    if len(airport_cell_indexes) == 0:
        return

    current_total = float(grid.loc[airport_cell_indexes, ["building_jobs", "poi_jobs", "landuse_jobs"]].sum().sum())
    if current_total >= AIRPORT_MINIMUM_JOBS:
        return

    bonus_total = AIRPORT_MINIMUM_JOBS - current_total
    weights = grid.loc[airport_cell_indexes, "airport_weight"].copy()
    positive = weights[weights > 0]

    if positive.sum() > 0:
        distribution = positive / positive.sum()
        for idx, fraction in distribution.items():
            grid.at[idx, "airport_bonus"] += bonus_total * float(fraction)
    else:
        even_share = bonus_total / len(airport_cell_indexes)
        grid.loc[airport_cell_indexes, "airport_bonus"] += even_share


def calibrate_jobs_and_filter(grid):
    grid["jobs_raw"] = grid["building_jobs"] + grid["poi_jobs"] + grid["landuse_jobs"] + grid["airport_bonus"]
    total_residents = float(grid["residents_raw"].sum())
    total_jobs_raw = float(grid["jobs_raw"].sum())
    if total_residents <= 0:
        raise SystemExit("Residents total from WorldPop is zero; cannot calibrate jobs.")
    if total_jobs_raw <= 0:
        raise SystemExit("Jobs total inferred from OSM is zero; cannot calibrate jobs.")

    scale = (TARGET_JOBS_SHARE * total_residents) / total_jobs_raw
    grid["jobs"] = (grid["jobs_raw"] * scale).round().clip(lower=0)
    grid["residents"] = grid["residents_raw"].round().clip(lower=0)

    top_jobs_ids = set(grid.nlargest(100, "jobs_raw")["id"])
    airport_mask = grid["airport_bonus"] > 0
    grid.loc[grid["jobs_raw"] > 0, "jobs"] = grid.loc[grid["jobs_raw"] > 0, "jobs"].clip(lower=5)
    grid.loc[airport_mask, "jobs"] = grid.loc[airport_mask, "jobs"].clip(lower=AIRPORT_MINIMUM_CELL_JOBS)
    grid.loc[grid["id"].isin(top_jobs_ids), "jobs"] = grid.loc[grid["id"].isin(top_jobs_ids), "jobs"].clip(
        lower=TOP_JOBS_MINIMUM_CELL_JOBS
    )

    retained = grid[(grid["residents"] >= 2) | (grid["jobs"] >= 5)].copy()
    if len(retained) < 2000:
        raise SystemExit(f"demand_seed retention is too low: {len(retained)} points retained, expected at least 2000.")

    retained["cluster_type"] = "low_density"
    retained.loc[
        (retained["jobs"] >= 50) & (retained["residents"] >= 50),
        "cluster_type",
    ] = "mixed_urban"
    retained.loc[
        (retained["residents"] >= 150) & ((retained["residents"] / retained["jobs"].clip(lower=1)) >= 2),
        "cluster_type",
    ] = "residential"
    retained.loc[
        (retained["jobs"] >= 250) & ((retained["jobs"] / retained["residents"].clip(lower=1)) >= 2),
        "cluster_type",
    ] = "employment_hub"
    retained.loc[retained["airport_bonus"] > 0, "cluster_type"] = "airport_hub"

    return retained


def _line_components(geometry):
    geom_type = geometry.geom_type
    if geom_type == "LineString":
        return [geometry]
    if geom_type == "MultiLineString":
        return [geom for geom in geometry.geoms if geom.length > 0]
    if geom_type == "GeometryCollection":
        parts = []
        for geom in geometry.geoms:
            parts.extend(_line_components(geom))
        return parts
    return []


def snap_points_to_roads(retained):
    gpd = import_dependency("geopandas")
    shapely = import_dependency("shapely")

    if not ROADS_NORMALIZED_PATH.exists():
        raise SystemExit(f"Missing normalized roads parquet: {ROADS_NORMALIZED_PATH}")

    roads = gpd.read_parquet(ROADS_NORMALIZED_PATH).to_crs("EPSG:3857")
    road_geometries = list(roads.geometry)
    road_tree = shapely.STRtree(road_geometries)

    final_points = []
    for row in retained.itertuples():
        cell_geom = row.geometry
        cell_center = cell_geom.centroid
        best_point = None

        road_indices = road_tree.query(cell_geom, predicate="intersects")
        longest = None
        longest_length = 0.0
        for idx in road_indices:
            clipped = road_geometries[int(idx)].intersection(cell_geom)
            for line in _line_components(clipped):
                if line.length > longest_length:
                    longest = line
                    longest_length = line.length

        if longest is not None and longest_length > 0:
            best_point = shapely.line_interpolate_point(longest, 0.5, normalized=True)
        else:
            nearest_idx = road_tree.nearest(cell_center)
            if nearest_idx is not None:
                nearest_geom = road_geometries[int(nearest_idx)]
                if nearest_geom.distance(cell_center) <= ROAD_SNAP_RADIUS_M:
                    nearest_distance = shapely.line_locate_point(nearest_geom, cell_center)
                    best_point = shapely.line_interpolate_point(nearest_geom, nearest_distance)

        final_points.append(best_point if best_point is not None else cell_center)

    snapped = retained.copy()
    snapped["geometry"] = final_points
    snapped = snapped.set_crs("EPSG:3857").to_crs("EPSG:4326")
    snapped["lon"] = snapped.geometry.x
    snapped["lat"] = snapped.geometry.y
    return snapped


def build_source_refs(retained) -> None:
    osm_stem = resolve_osm_pbf_path().name.replace(".osm.pbf", "")
    base = f"worldpop:2025;osm:{osm_stem};grid:{int(DEMAND_GRID_CELL_SIZE_M)}m"
    retained["source_refs"] = base
    retained.loc[retained["airport_bonus"] > 0, "source_refs"] = retained.loc[
        retained["airport_bonus"] > 0, "source_refs"
    ] + ";airport_bonus"


def verify_resident_total(retained) -> None:
    residents_seed = float(retained["residents"].sum())
    residents_worldpop = float(retained["residents_raw"].sum())
    if residents_worldpop <= 0:
        raise SystemExit("Residents raw total is zero after retention.")
    delta_ratio = abs(residents_seed - residents_worldpop) / residents_worldpop
    if delta_ratio > 0.01:
        raise SystemExit(
            f"Retained residents total drifted from WorldPop by {delta_ratio:.2%}; expected at most 1%."
        )


def main() -> None:
    args = parse_args()
    ensure_directories()

    grid, grid_bounds = create_grid(DEMAND_GRID_CELL_SIZE_M)
    load_worldpop_residents(args.worldpop, grid, grid_bounds, DEMAND_GRID_CELL_SIZE_M)
    employment_buildings = load_building_jobs(grid, grid_bounds, DEMAND_GRID_CELL_SIZE_M)
    load_poi_jobs(grid, grid_bounds, DEMAND_GRID_CELL_SIZE_M, employment_buildings)
    load_landuse_jobs(grid, employment_buildings)
    apply_airport_bonus(grid)

    retained = calibrate_jobs_and_filter(grid)
    snapped = snap_points_to_roads(retained)
    build_source_refs(snapped)
    verify_resident_total(snapped)

    output_columns = [
        "id",
        "lon",
        "lat",
        "jobs",
        "residents",
        "source_refs",
        "cluster_type",
        "jobs_raw",
        "residents_raw",
        "building_jobs",
        "poi_jobs",
        "landuse_jobs",
        "airport_bonus",
        "col",
        "row",
    ]
    snapped["cell_size_m"] = DEMAND_GRID_CELL_SIZE_M
    snapped[output_columns + ["cell_size_m"]].to_csv(args.output, index=False)
    print(f"Wrote demand seed to {args.output}")


if __name__ == "__main__":
    main()
