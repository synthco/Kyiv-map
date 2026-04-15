from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from config import BBOX, resolve_osm_pbf_path
from common import import_dependency


@dataclass
class ExtractionStats:
    scanned: int = 0
    accepted: int = 0
    skipped: int = 0
    invalid_geometry: int = 0
    final_count: int = 0


def _normalize_gdf(records: list[dict], stats: ExtractionStats, layer_name: str):
    gpd = import_dependency("geopandas")

    if not records:
        raise SystemExit(f"No {layer_name} features were extracted from the OSM PBF.")

    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
    clipped = gpd.clip(gdf, BBOX).copy()
    stats.final_count = len(clipped)
    print(
        f"[osm_reader:{layer_name}] scanned={stats.scanned} "
        f"accepted={stats.accepted} skipped={stats.skipped} "
        f"invalid_geometry={stats.invalid_geometry} final_count={stats.final_count}"
    )

    if clipped.empty:
        raise SystemExit(f"All extracted {layer_name} features were clipped away by the KYV bbox.")

    return clipped


def _osm_pbf_path():
    osm_pbf_path = resolve_osm_pbf_path()
    if not osm_pbf_path.exists():
        raise SystemExit(f"Missing OSM source file: {osm_pbf_path}")
    return osm_pbf_path


def _string_tag(tags, key: str) -> str:
    return str(tags.get(key, "")).strip()


def _line_records_for_key(
    key: str,
    values: Iterable[str] | None,
    layer_name: str,
    record_builder: Callable[[object], dict],
):
    osmium = import_dependency("osmium", "osmium")
    shapely_wkb = import_dependency("shapely.wkb", "shapely")

    stats = ExtractionStats()
    allowed_values = set(values) if values is not None else None
    factory = osmium.geom.WKBFactory()
    records: list[dict] = []

    processor = (
        osmium.FileProcessor(str(_osm_pbf_path()))
        .with_locations()
        .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
        .with_filter(osmium.filter.KeyFilter(key))
    )

    for way in processor:
        stats.scanned += 1
        tag_value = _string_tag(way.tags, key)
        if allowed_values is not None and tag_value not in allowed_values:
            stats.skipped += 1
            continue

        try:
            geometry = shapely_wkb.loads(factory.create_linestring(way.nodes), hex=True)
        except (osmium.InvalidLocationError, RuntimeError, ValueError):
            stats.invalid_geometry += 1
            continue

        record = record_builder(way)
        record["geometry"] = geometry
        records.append(record)
        stats.accepted += 1

    return _normalize_gdf(records, stats, layer_name)


def _area_records_for_key(
    key: str,
    values: Iterable[str] | None,
    layer_name: str,
    record_builder: Callable[[object], dict],
):
    osmium = import_dependency("osmium", "osmium")
    shapely_wkb = import_dependency("shapely.wkb", "shapely")

    stats = ExtractionStats()
    allowed_values = set(values) if values is not None else None
    factory = osmium.geom.WKBFactory()
    records: list[dict] = []

    processor = (
        osmium.FileProcessor(str(_osm_pbf_path()))
        .with_areas()
        .with_filter(osmium.filter.KeyFilter(key))
    )

    for obj in processor:
        if not obj.is_area():
            continue

        stats.scanned += 1
        tag_value = _string_tag(obj.tags, key)
        if not tag_value:
            stats.skipped += 1
            continue
        if allowed_values is not None and tag_value not in allowed_values:
            stats.skipped += 1
            continue

        try:
            geometry = shapely_wkb.loads(factory.create_multipolygon(obj), hex=True)
        except (osmium.InvalidLocationError, RuntimeError, ValueError):
            stats.invalid_geometry += 1
            continue

        record = record_builder(obj)
        record["geometry"] = geometry
        records.append(record)
        stats.accepted += 1

    return _normalize_gdf(records, stats, layer_name)


def load_highway_features(bbox=BBOX):
    return _line_records_for_key(
        key="highway",
        values=None,
        layer_name="roads",
        record_builder=lambda way: {
            "source_osm_id": str(way.id),
            "highway": _string_tag(way.tags, "highway"),
            "name": _string_tag(way.tags, "name"),
            "bridge": _string_tag(way.tags, "bridge"),
            "tunnel": _string_tag(way.tags, "tunnel"),
            "ford": _string_tag(way.tags, "ford"),
        },
    )


def load_aeroway_features(bbox=BBOX, values=("runway", "taxiway")):
    return _line_records_for_key(
        key="aeroway",
        values=values,
        layer_name="runways_taxiways",
        record_builder=lambda way: {
            "source_osm_id": str(way.id),
            "aeroway": _string_tag(way.tags, "aeroway"),
            "name": _string_tag(way.tags, "name"),
            "surface": _string_tag(way.tags, "surface"),
        },
    )


def load_building_features(bbox=BBOX):
    return _area_records_for_key(
        key="building",
        values=None,
        layer_name="buildings",
        record_builder=lambda obj: {
            "source_osm_id": str(obj.id),
            "building": _string_tag(obj.tags, "building"),
            "name": _string_tag(obj.tags, "name"),
            "building_levels": _string_tag(obj.tags, "building:levels"),
            "office": _string_tag(obj.tags, "office"),
            "shop": _string_tag(obj.tags, "shop"),
            "amenity": _string_tag(obj.tags, "amenity"),
            "tourism": _string_tag(obj.tags, "tourism"),
            "railway": _string_tag(obj.tags, "railway"),
            "public_transport": _string_tag(obj.tags, "public_transport"),
            "aeroway": _string_tag(obj.tags, "aeroway"),
            "government": _string_tag(obj.tags, "government"),
        },
    )


def load_landuse_features(bbox=BBOX, values=("industrial", "commercial", "retail", "railway", "port", "construction")):
    return _area_records_for_key(
        key="landuse",
        values=values,
        layer_name="landuse",
        record_builder=lambda obj: {
            "source_osm_id": str(obj.id),
            "landuse": _string_tag(obj.tags, "landuse"),
            "name": _string_tag(obj.tags, "name"),
        },
    )


def load_aerodrome_features(bbox=BBOX):
    return _area_records_for_key(
        key="aeroway",
        values=("aerodrome",),
        layer_name="aerodromes",
        record_builder=lambda obj: {
            "source_osm_id": str(obj.id),
            "aeroway": _string_tag(obj.tags, "aeroway"),
            "name": _string_tag(obj.tags, "name"),
            "iata": _string_tag(obj.tags, "iata"),
            "icao": _string_tag(obj.tags, "icao"),
        },
    )


def load_poi_features(bbox=BBOX):
    osmium = import_dependency("osmium", "osmium")
    shapely_geometry = import_dependency("shapely.geometry", "shapely")
    shapely_wkb = import_dependency("shapely.wkb", "shapely")

    class PoiHandler(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.stats = ExtractionStats()
            self.factory = osmium.geom.WKBFactory()
            self.records: list[dict] = []

        @staticmethod
        def _extract_tags(tags) -> dict[str, str]:
            return {
                "source_osm_id": "",
                "office": _string_tag(tags, "office"),
                "shop": _string_tag(tags, "shop"),
                "amenity": _string_tag(tags, "amenity"),
                "railway": _string_tag(tags, "railway"),
                "public_transport": _string_tag(tags, "public_transport"),
                "tourism": _string_tag(tags, "tourism"),
                "name": _string_tag(tags, "name"),
            }

        @staticmethod
        def _is_supported(record: dict[str, str]) -> bool:
            return any(
                (
                    record["office"],
                    record["shop"],
                    record["amenity"],
                    record["railway"],
                    record["public_transport"],
                    record["tourism"],
                )
            )

        def node(self, node):
            self.stats.scanned += 1
            record = self._extract_tags(node.tags)
            if not self._is_supported(record):
                self.stats.skipped += 1
                return

            record["source_osm_id"] = f"node/{node.id}"
            record["geometry"] = shapely_geometry.Point(node.location.lon, node.location.lat)
            self.records.append(record)
            self.stats.accepted += 1

        def area(self, area):
            self.stats.scanned += 1
            record = self._extract_tags(area.tags)
            if not self._is_supported(record):
                self.stats.skipped += 1
                return

            try:
                polygon = shapely_wkb.loads(self.factory.create_multipolygon(area), hex=True)
            except (osmium.InvalidLocationError, RuntimeError, ValueError):
                self.stats.invalid_geometry += 1
                return

            record["source_osm_id"] = f"area/{area.id}"
            record["geometry"] = polygon.centroid
            self.records.append(record)
            self.stats.accepted += 1

    handler = PoiHandler()
    handler.apply_file(str(_osm_pbf_path()), locations=True)
    return _normalize_gdf(handler.records, handler.stats, "pois")
