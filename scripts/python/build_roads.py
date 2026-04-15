from __future__ import annotations

import argparse

from config import ROAD_CLASS_VOCAB, ROADS_NORMALIZED_PATH, ROADS_OUTPUT_PATH, STRUCTURE_VOCAB
from common import ensure_directories, write_gzip_text
from osm_reader import load_highway_features


def normalize_road_class(highway_value: str | None) -> str:
    if not highway_value:
        return "other"

    if highway_value.endswith("_link"):
        return "link"

    if highway_value in ROAD_CLASS_VOCAB:
        return highway_value

    return "other"


def normalize_structure(row) -> str:
    if str(row.get("bridge", "")).lower() not in {"", "nan", "none", "false", "0"}:
        return "bridge"
    if str(row.get("tunnel", "")).lower() not in {"", "nan", "none", "false", "0"}:
        return "tunnel"
    if str(row.get("ford", "")).lower() not in {"", "nan", "none", "false", "0"}:
        return "ford"
    return "ground"


def build_roads() -> None:
    roads = load_highway_features()
    roads["id"] = [f"road-{idx}" for idx in range(len(roads))]
    roads["roadClass"] = roads["highway"].map(normalize_road_class)
    roads["structure"] = roads.apply(normalize_structure, axis=1)
    roads["name"] = roads["name"].fillna("")
    roads = roads[["id", "roadClass", "structure", "name", "geometry"]]

    invalid_structure = sorted(set(roads["structure"]) - set(STRUCTURE_VOCAB))
    if invalid_structure:
        raise SystemExit(f"Invalid normalized structure values: {invalid_structure}")

    roads.to_parquet(ROADS_NORMALIZED_PATH)
    write_gzip_text(ROADS_OUTPUT_PATH, roads.to_json(drop_id=True))


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description="Extract, normalize, and serialize drivable roads for the KYV geodata pipeline.").parse_args()


def main() -> None:
    parse_args()
    ensure_directories()
    build_roads()
    print(f"Wrote normalized roads to {ROADS_NORMALIZED_PATH}")
    print(f"Wrote served roads output to {ROADS_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
