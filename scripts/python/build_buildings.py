from __future__ import annotations

import argparse
import math

from config import (
    BUILDINGS_INDEX_OUTPUT_PATH,
    BUILDINGS_NORMALIZED_PATH,
    BUILDING_GRID_CELL_SIZE,
    DEFAULT_FOUNDATION_DEPTH,
    BBOX,
)
from common import ensure_directories, write_gzip_json
from osm_reader import load_building_features


def geometry_to_polygon_coords(geometry) -> list[list[float]]:
    if geometry.geom_type == "Polygon":
        polygon = geometry
    elif geometry.geom_type == "MultiPolygon":
        polygon = max(geometry.geoms, key=lambda item: item.area)
    else:
        raise ValueError(f"Unsupported building geometry type: {geometry.geom_type}")

    return [[float(x), float(y)] for x, y in polygon.exterior.coords[:-1]]


def compile_buildings_index(buildings) -> dict:
    min_lon, min_lat, max_lon, max_lat = BBOX
    cols = max(1, math.ceil((max_lon - min_lon) / BUILDING_GRID_CELL_SIZE))
    rows = max(1, math.ceil((max_lat - min_lat) / BUILDING_GRID_CELL_SIZE))
    cell_map: dict[tuple[int, int], list[int]] = {}
    serialized_buildings = []

    for idx, row in buildings.reset_index(drop=True).iterrows():
        polygon = geometry_to_polygon_coords(row.geometry)
        b_min_lon, b_min_lat, b_max_lon, b_max_lat = row.geometry.bounds
        foundation_depth = float(row.get("foundationDepth", DEFAULT_FOUNDATION_DEPTH))
        serialized_buildings.append(
            {
                "b": [b_min_lon, b_min_lat, b_max_lon, b_max_lat],
                "f": foundation_depth,
                "p": polygon,
            }
        )

        col_start = max(0, int((b_min_lon - min_lon) / BUILDING_GRID_CELL_SIZE))
        col_end = min(cols - 1, int((b_max_lon - min_lon) / BUILDING_GRID_CELL_SIZE))
        row_start = max(0, int((b_min_lat - min_lat) / BUILDING_GRID_CELL_SIZE))
        row_end = min(rows - 1, int((b_max_lat - min_lat) / BUILDING_GRID_CELL_SIZE))

        for col in range(col_start, col_end + 1):
            for grid_row in range(row_start, row_end + 1):
                cell_map.setdefault((col, grid_row), []).append(idx)

    cells = [[col, grid_row, *building_ids] for (col, grid_row), building_ids in sorted(cell_map.items())]
    max_depth = max((building["f"] for building in serialized_buildings), default=DEFAULT_FOUNDATION_DEPTH)

    return {
        "cs": BUILDING_GRID_CELL_SIZE,
        "bbox": [min_lon, min_lat, max_lon, max_lat],
        "grid": [cols, rows],
        "cells": cells,
        "buildings": serialized_buildings,
        "stats": {
            "count": len(serialized_buildings),
            "maxDepth": max_depth,
        },
    }


def build_buildings() -> None:
    buildings = load_building_features()
    buildings["id"] = [f"building-{idx}" for idx in range(len(buildings))]
    buildings["foundationDepth"] = DEFAULT_FOUNDATION_DEPTH
    buildings = buildings[["id", "foundationDepth", "geometry"]]

    buildings.to_parquet(BUILDINGS_NORMALIZED_PATH)
    write_gzip_json(BUILDINGS_INDEX_OUTPUT_PATH, compile_buildings_index(buildings))


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description="Extract building polygons and compile the optimized buildings index for KYV.").parse_args()


def main() -> None:
    parse_args()
    ensure_directories()
    build_buildings()
    print(f"Wrote normalized buildings to {BUILDINGS_NORMALIZED_PATH}")
    print(f"Wrote buildings index to {BUILDINGS_INDEX_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
