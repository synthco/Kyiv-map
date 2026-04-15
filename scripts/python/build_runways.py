from __future__ import annotations

import argparse

from config import RUNWAYS_NORMALIZED_PATH, RUNWAYS_OUTPUT_PATH
from common import ensure_directories, write_gzip_text
from osm_reader import load_aeroway_features


def build_runways() -> None:
    runways = load_aeroway_features()
    runways["id"] = [f"runway-{idx}" for idx in range(len(runways))]
    runways["name"] = runways["name"].fillna("")
    runways["surface"] = runways["surface"].fillna("")
    runways = runways[["id", "aeroway", "name", "surface", "geometry"]]

    runways.to_parquet(RUNWAYS_NORMALIZED_PATH)
    write_gzip_text(RUNWAYS_OUTPUT_PATH, runways.to_json(drop_id=True))


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description="Extract runway and taxiway features for the KYV geodata pipeline.").parse_args()


def main() -> None:
    parse_args()
    ensure_directories()
    build_runways()
    print(f"Wrote normalized runways to {RUNWAYS_NORMALIZED_PATH}")
    print(f"Wrote served runways output to {RUNWAYS_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
