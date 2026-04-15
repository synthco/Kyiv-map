from __future__ import annotations

import argparse
import json
import math

from config import (
    COMMUTE_PRIMARY_MAX_DISTANCE_KM,
    DEMAND_COMMUTE_SHARE,
    DEMAND_DATA_OUTPUT_PATH,
    DEMAND_POINTS_PATH,
    DEMAND_ROUTE_CACHE_PATH,
    EMPLOYMENT_HUB_MIN_JOBS,
    EMPLOYMENT_HUB_TOP_PERCENTILE,
    OSRM_BASE_URL,
)
from common import ensure_directories, import_dependency, write_gzip_json


def load_route_cache() -> dict[str, dict]:
    if not DEMAND_ROUTE_CACHE_PATH.exists():
        return {}
    return json.loads(DEMAND_ROUTE_CACHE_PATH.read_text(encoding="utf-8"))


def save_route_cache(cache: dict[str, dict]) -> None:
    DEMAND_ROUTE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEMAND_ROUTE_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def query_osrm_route(origin_id: str, origin: list[float], destination_id: str, destination: list[float], cache: dict[str, dict]) -> dict | None:
    requests = import_dependency("requests")
    cache_key = f"{origin_id}|{destination_id}"
    if cache_key in cache:
        cached = cache[cache_key]
        return cached if cached.get("status") == "ok" else None

    url = (
        f"{OSRM_BASE_URL}/route/v1/driving/"
        f"{origin[0]},{origin[1]};{destination[0]},{destination[1]}"
        "?overview=full&geometries=geojson"
    )

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    payload = response.json()
    routes = payload.get("routes") or []
    if not routes:
        cache[cache_key] = {"status": "no_route"}
        return None

    route = routes[0]
    geometry = route.get("geometry", {})
    coordinates = geometry.get("coordinates") or []
    result = {
        "status": "ok",
        "drivingSeconds": float(route["duration"]),
        "drivingDistance": float(route["distance"]),
        "drivingPath": coordinates,
    }
    cache[cache_key] = result
    return result


def compute_hub_candidates(projected) -> tuple[set[str], object]:
    employment_points = projected[projected["jobs"] > 0].copy()
    if employment_points.empty:
        raise SystemExit("Demand points must include at least one jobs cluster.")

    top_n = max(1, math.ceil(len(projected) * EMPLOYMENT_HUB_TOP_PERCENTILE))
    top_jobs_ids = set(projected.nlargest(top_n, "jobs")["id"])
    hub_ids = set(employment_points[employment_points["jobs"] >= EMPLOYMENT_HUB_MIN_JOBS]["id"]) | top_jobs_ids
    return hub_ids, employment_points


def pick_destination_candidates(origin_row, projected, hubs) -> list[dict]:
    candidates: list[dict] = []
    origin_geom = origin_row.geometry

    for hub in hubs.itertuples():
        if hub.id == origin_row.id:
            continue
        distance_km = float(origin_geom.distance(hub.geometry) / 1000.0)
        score = float(hub.jobs) / (1.0 + (distance_km ** 1.6))
        candidates.append(
            {
                "id": str(hub.id),
                "coords": [float(hub.coords[0]), float(hub.coords[1])],
                "distance_km": distance_km,
                "score": score,
                "jobs": float(hub.jobs),
            }
        )

    if not candidates:
        return []

    near = [candidate for candidate in candidates if candidate["distance_km"] <= COMMUTE_PRIMARY_MAX_DISTANCE_KM]
    if near:
        return sorted(near, key=lambda candidate: candidate["score"], reverse=True)

    return sorted(candidates, key=lambda candidate: candidate["score"], reverse=True)


def build_demand_data() -> None:
    gpd = import_dependency("geopandas")

    if not DEMAND_POINTS_PATH.exists():
        raise SystemExit(f"Missing normalized demand points file: {DEMAND_POINTS_PATH}")

    gdf = gpd.read_parquet(DEMAND_POINTS_PATH)
    if gdf.empty:
        raise SystemExit("Normalized demand points dataset is empty.")

    projected = gdf.to_crs("EPSG:3857")
    residential_points = projected[projected["residents"] > 0].copy()
    if residential_points.empty:
        raise SystemExit("Demand points must include at least one residents cluster.")

    hub_ids, employment_points = compute_hub_candidates(projected)
    hubs = employment_points[employment_points["id"].isin(hub_ids)].copy()
    if hubs.empty:
        raise SystemExit("No employment hubs were derived from normalized demand points.")

    points = []
    pop_ids_by_point: dict[str, list[str]] = {}
    for row in gdf.itertuples():
        point_id = str(row.id)
        points.append(
            {
                "id": point_id,
                "location": [float(row.coords[0]), float(row.coords[1])],
                "jobs": int(max(0, round(float(row.jobs)))),
                "residents": int(max(0, round(float(row.residents)))),
                "popIds": [],
            }
        )
        pop_ids_by_point[point_id] = []

    route_cache = load_route_cache()
    pops = []
    pop_index = 0

    for origin in residential_points.itertuples():
        candidate_destinations = pick_destination_candidates(origin, projected, hubs)
        if not candidate_destinations:
            continue

        origin_id = str(origin.id)
        origin_coords = [float(origin.coords[0]), float(origin.coords[1])]
        route_result = None
        chosen_destination = None

        for candidate in candidate_destinations:
            if origin_coords == candidate["coords"]:
                continue
            route_result = query_osrm_route(origin_id, origin_coords, candidate["id"], candidate["coords"], route_cache)
            if route_result and route_result["drivingSeconds"] > 0 and route_result["drivingDistance"] > 0:
                chosen_destination = candidate
                break

        if route_result is None or chosen_destination is None:
            continue

        pop_size = int(max(1, round(float(origin.residents) * DEMAND_COMMUTE_SHARE)))
        pop_id = f"pop-{pop_index}"
        pop_index += 1

        pops.append(
            {
                "id": pop_id,
                "size": pop_size,
                "residenceId": origin_id,
                "jobId": chosen_destination["id"],
                "drivingSeconds": route_result["drivingSeconds"],
                "drivingDistance": route_result["drivingDistance"],
                "drivingPath": route_result["drivingPath"],
            }
        )
        pop_ids_by_point[origin_id].append(pop_id)
        pop_ids_by_point[chosen_destination["id"]].append(pop_id)

    for point in points:
        point["popIds"] = pop_ids_by_point[point["id"]]

    if not pops:
        raise SystemExit("OSRM routing did not yield any valid commute pairs; demand_data would be empty.")

    save_route_cache(route_cache)
    write_gzip_json(
        DEMAND_DATA_OUTPUT_PATH,
        {
            "points": points,
            "pops": pops,
        },
    )


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description="Generate demand_data.json.gz from normalized clustered demand points.").parse_args()


def main() -> None:
    parse_args()
    ensure_directories()
    build_demand_data()
    print(f"Wrote demand data to {DEMAND_DATA_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
