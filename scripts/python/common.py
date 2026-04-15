from __future__ import annotations

import gzip
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

from config import (
    BBOX,
    BBOX_MANIFEST_PATH,
    BUILD_DIR,
    CITY_DATA_DIR,
    DATA_SRC_DIR,
    GENERATED_DIR,
    OSM_DIR,
    OPEN_DATA_DIR,
    VALIDATION_DIR,
)


def ensure_directories() -> None:
    for path in (
        DATA_SRC_DIR,
        OSM_DIR,
        OPEN_DATA_DIR,
        BUILD_DIR,
        VALIDATION_DIR,
        GENERATED_DIR,
        CITY_DATA_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def bbox_record() -> dict[str, Any]:
    min_lon, min_lat, max_lon, max_lat = BBOX
    return {
        "bbox": [min_lon, min_lat, max_lon, max_lat],
        "crs": "EPSG:4326",
        "coordinate_order": "[longitude, latitude]",
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_gzip_json(path: Path, payload: Any) -> None:
    write_gzip_text(path, json.dumps(payload, ensure_ascii=False))


def write_gzip_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_dependency(module_name: str, package_name: str | None = None):
    package_name = package_name or module_name
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise SystemExit(
            f"Missing Python dependency '{package_name}'. "
            f"Create a venv and install requirements with "
            f"'python3 -m venv .venv && .venv/bin/pip install -r requirements.txt'."
        ) from exc


def write_bbox_manifest() -> None:
    write_json(BBOX_MANIFEST_PATH, bbox_record())


def file_status(path: Path) -> dict[str, Any]:
    status = {
        "path": str(path),
        "exists": path.exists(),
    }
    if path.exists():
        status["size_bytes"] = path.stat().st_size
        status["sha256"] = sha256_file(path)
    return status
