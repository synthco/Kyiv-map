from __future__ import annotations

import argparse
from pathlib import Path

from config import BBOX, DEMAND_POINTS_PATH, DEMAND_SEED_PATH
from common import ensure_directories, import_dependency


REQUIRED_COLUMNS = {"lon", "lat", "jobs", "residents"}


def load_seed_dataframe(seed_path: Path):
    pandas = import_dependency("pandas")
    suffix = seed_path.suffix.lower()

    if suffix == ".csv":
        return pandas.read_csv(seed_path)
    if suffix == ".parquet":
        return pandas.read_parquet(seed_path)

    raise SystemExit(f"Unsupported demand seed format: {seed_path}")


def build_demand_points(seed_path: Path) -> None:
    gpd = import_dependency("geopandas")

    if not seed_path.exists():
        raise SystemExit(
            f"Missing demand seed file: {seed_path}. "
            f"Expected columns: {sorted(REQUIRED_COLUMNS)} plus optional id/source_refs/cluster_type."
        )

    df = load_seed_dataframe(seed_path)
    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        raise SystemExit(f"Demand seed is missing required columns: {sorted(missing_columns)}")

    df = df.copy()
    if "id" not in df.columns:
        df["id"] = [f"demand-{idx}" for idx in range(len(df))]
    if "source_refs" not in df.columns:
        df["source_refs"] = "manual_seed"
    if "cluster_type" not in df.columns:
        df["cluster_type"] = "seed"

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs="EPSG:4326",
    )
    gdf = gpd.clip(gdf, BBOX).copy()
    gdf["jobs"] = gdf["jobs"].fillna(0).clip(lower=0)
    gdf["residents"] = gdf["residents"].fillna(0).clip(lower=0)
    gdf["coords"] = gdf.geometry.apply(lambda geom: [float(geom.x), float(geom.y)])
    ordered = ["id", "coords", "jobs", "residents", "source_refs", "cluster_type"]
    remaining = [column for column in gdf.columns if column not in ordered and column != "geometry"]
    gdf = gdf[ordered + remaining + ["geometry"]]

    if gdf.empty:
        raise SystemExit("Demand seed produced no demand points inside the KYV bbox.")

    gdf.to_parquet(DEMAND_POINTS_PATH)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize clustered demand points into GeoParquet for the KYV pipeline.")
    parser.add_argument("--seed", type=Path, default=DEMAND_SEED_PATH, help="Path to the demand seed CSV or Parquet.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_directories()
    build_demand_points(args.seed)
    print(f"Wrote normalized demand points to {DEMAND_POINTS_PATH}")


if __name__ == "__main__":
    main()
