from __future__ import annotations

import argparse
from pathlib import Path

from config import BBOX
from common import ensure_directories, import_dependency, write_bbox_manifest


def write_geodataframe(gdf, output_path: Path) -> None:
    suffix = output_path.suffix.lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if suffix == ".parquet":
        gdf.to_parquet(output_path)
        return
    if suffix == ".geojson":
        output_path.write_text(gdf.to_json(drop_id=True), encoding="utf-8")
        return
    if suffix == ".gpkg":
        gdf.to_file(output_path, driver="GPKG")
        return

    raise SystemExit(f"Unsupported output format for {output_path}")


def clip_dataset(input_path: Path, output_path: Path, layer: str | None) -> None:
    gpd = import_dependency("geopandas")
    pyogrio = import_dependency("pyogrio")

    gdf = pyogrio.read_dataframe(input_path, layer=layer, bbox=BBOX, use_arrow=True)
    if gdf.empty:
        raise SystemExit(f"No features found inside the KYV bbox for {input_path}")

    if gdf.crs is None:
        raise SystemExit(f"Input dataset {input_path} has no CRS; cannot normalize to EPSG:4326")

    if str(gdf.crs).upper() != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")

    clipped = gpd.clip(gdf, BBOX)
    if clipped.empty:
        raise SystemExit(f"All features were clipped away for {input_path}")

    write_geodataframe(clipped, output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write the canonical KYV bbox manifest or clip a vector dataset to the bbox.")
    parser.add_argument("--input", type=Path, help="Optional input vector dataset to clip.")
    parser.add_argument("--output", type=Path, help="Optional output path for the clipped dataset.")
    parser.add_argument("--layer", help="Optional layer name for multi-layer vector sources.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_directories()
    write_bbox_manifest()

    if not args.input:
        print("Wrote bbox manifest for KYV.")
        return

    if not args.output:
        raise SystemExit("--output is required when --input is provided")

    clip_dataset(args.input, args.output, args.layer)
    print(f"Clipped {args.input} to {args.output}")


if __name__ == "__main__":
    main()
