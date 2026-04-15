from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from config import (
    BBOX,
    BUILDINGS_INDEX_OUTPUT_PATH,
    DEMAND_DATA_OUTPUT_PATH,
    ROADS_OUTPUT_PATH,
    RUNWAYS_OUTPUT_PATH,
    VALIDATION_REPORT_PATH,
)
from common import ensure_directories, write_json


def load_gzip_json(path: Path):
    if not path.exists():
        raise SystemExit(f"Missing generated file: {path}")
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def coordinate_is_valid(coord) -> bool:
    return (
        isinstance(coord, list)
        and len(coord) == 2
        and -180 <= float(coord[0]) <= 180
        and -90 <= float(coord[1]) <= 90
    )


def bbox_contains(coord) -> bool:
    min_lon, min_lat, max_lon, max_lat = BBOX
    return min_lon <= float(coord[0]) <= max_lon and min_lat <= float(coord[1]) <= max_lat


def validate_demand_data(payload) -> list[str]:
    errors: list[str] = []
    points = payload.get("points") or []
    pops = payload.get("pops") or []
    if not points:
        errors.append("Demand data contains no points.")
    if not pops:
        errors.append("Demand data contains no pops.")
    point_ids = {point.get("id") for point in points}
    pop_ids = {pop.get("id") for pop in pops}

    for point in points:
        location = point.get("location")
        if not coordinate_is_valid(location):
            errors.append(f"Invalid point location: {point.get('id')}")
            continue
        if not bbox_contains(location):
            errors.append(f"Point outside bbox: {point.get('id')}")
        if point.get("jobs", -1) < 0 or point.get("residents", -1) < 0:
            errors.append(f"Negative jobs/residents for point: {point.get('id')}")
        for pop_id in point.get("popIds") or []:
            if pop_id not in pop_ids:
                errors.append(f"Point references missing pop id: {pop_id}")

    for pop in pops:
        if pop.get("residenceId") not in point_ids:
            errors.append(f"Pop references missing residenceId: {pop.get('id')}")
        if pop.get("jobId") not in point_ids:
            errors.append(f"Pop references missing jobId: {pop.get('id')}")
        if float(pop.get("size", 0)) <= 0:
            errors.append(f"Pop has non-positive size: {pop.get('id')}")
        if float(pop.get("drivingSeconds", 0)) <= 0 or float(pop.get("drivingDistance", 0)) <= 0:
            errors.append(f"Pop has non-positive routing metrics: {pop.get('id')}")
        path = pop.get("drivingPath") or []
        for coord in path:
            if not coordinate_is_valid(coord):
                errors.append(f"Invalid drivingPath coordinate in pop: {pop.get('id')}")
                break

    return errors


def validate_buildings_index(payload) -> list[str]:
    errors: list[str] = []
    bbox = payload.get("bbox")
    if bbox != list(BBOX):
        errors.append("Buildings index bbox does not match canonical KYV bbox.")
    if not isinstance(payload.get("grid"), list) or len(payload["grid"]) != 2:
        errors.append("Buildings index grid must be a 2-item list.")

    for building in payload.get("buildings") or []:
        for coord in building.get("p") or []:
            if not coordinate_is_valid(coord):
                errors.append("Invalid building polygon coordinate.")
                break

    return errors


def validate_feature_collection(payload, layer_name: str) -> list[str]:
    errors: list[str] = []
    if payload.get("type") != "FeatureCollection":
        errors.append(f"{layer_name} is not a GeoJSON FeatureCollection.")
        return errors

    for feature in payload.get("features") or []:
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates")
        if geometry.get("type") not in {"LineString", "MultiLineString", "Polygon", "MultiPolygon"}:
            errors.append(f"{layer_name} has unsupported geometry type: {geometry.get('type')}")
        if layer_name == "roads":
            properties = feature.get("properties") or {}
            for key in ("roadClass", "structure", "name"):
                if key not in properties:
                    errors.append(f"roads feature missing property: {key}")

        def walk(node):
            if isinstance(node, list) and node and isinstance(node[0], (int, float)):
                if not coordinate_is_valid(node) or not bbox_contains(node):
                    errors.append(f"{layer_name} contains coordinate outside bbox or valid range.")
                return
            if isinstance(node, list):
                for child in node:
                    walk(child)

        walk(coordinates)

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated KYV city-data artifacts against the local geodata contract.")
    parser.add_argument("--strict", action="store_true", help="Exit with a non-zero status code if any validation errors are found.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_directories()

    report = {
        "demand_data": {
            "path": str(DEMAND_DATA_OUTPUT_PATH),
            "errors": validate_demand_data(load_gzip_json(DEMAND_DATA_OUTPUT_PATH)),
        },
        "buildings_index": {
            "path": str(BUILDINGS_INDEX_OUTPUT_PATH),
            "errors": validate_buildings_index(load_gzip_json(BUILDINGS_INDEX_OUTPUT_PATH)),
        },
        "roads": {
            "path": str(ROADS_OUTPUT_PATH),
            "errors": validate_feature_collection(load_gzip_json(ROADS_OUTPUT_PATH), "roads"),
        },
        "runways_taxiways": {
            "path": str(RUNWAYS_OUTPUT_PATH),
            "errors": validate_feature_collection(load_gzip_json(RUNWAYS_OUTPUT_PATH), "runways_taxiways"),
        },
        "runtime_schema_validation": {
            "status": "pending_runtime_confirmation",
            "notes": [
                "Confirm whether the runway schema key is RunwaysTaxiwaysSchema or RunwaysTaxiwaysGeojsonSchema.",
                "Run Subway Builder runtime schema validation after the key is confirmed.",
            ],
        },
    }

    write_json(VALIDATION_REPORT_PATH, report)
    all_errors = [error for section in report.values() if isinstance(section, dict) for error in section.get("errors", [])]

    print(f"Wrote validation report to {VALIDATION_REPORT_PATH}")
    if all_errors:
        print("Validation errors detected:")
        for error in all_errors:
            print(f"  - {error}")
        if args.strict:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
