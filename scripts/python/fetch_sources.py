from __future__ import annotations

import argparse
from datetime import datetime, timezone

from config import SOURCE_MANIFEST_PATH, SOURCE_SPECS, resolve_osm_pbf_path
from common import ensure_directories, file_status, import_dependency, write_json


def download_file(url: str, destination):
    requests = import_dependency("requests")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def build_manifest(manifest_only: bool, force: bool) -> dict:
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
    }

    for source_id, spec in SOURCE_SPECS.items():
        path = spec["path"]
        mode = spec["mode"]
        required = spec["required"]
        resolved_path = resolve_osm_pbf_path() if source_id == "osm_ukraine_pbf" else path

        entry = {
            "description": spec["description"],
            "mode": mode,
            "required": required,
            "url": spec["url"],
            "canonical_path": str(path),
        }

        if mode == "download" and not manifest_only:
            if force or not resolved_path.exists():
                download_file(spec["url"], path)
                entry["status"] = "downloaded"
            else:
                entry["status"] = "cached" if resolved_path == path else "resolved_local_file"
        elif mode == "manual":
            entry["status"] = "present" if resolved_path.exists() else "pending_manual_source"
        else:
            entry["status"] = "skipped"

        entry.update(file_status(resolved_path))
        manifest["sources"][source_id] = entry

    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch or verify raw data sources for the KYV ETL pipeline.")
    parser.add_argument("--manifest-only", action="store_true", help="Write the source manifest without downloading files.")
    parser.add_argument("--force", action="store_true", help="Re-download auto-managed files even if they already exist.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_directories()
    manifest = build_manifest(manifest_only=args.manifest_only, force=args.force)
    write_json(SOURCE_MANIFEST_PATH, manifest)

    missing_required = [
        source_id
        for source_id, source in manifest["sources"].items()
        if SOURCE_SPECS[source_id]["required"] and not source["exists"]
    ]
    if missing_required:
        print("Source manifest written, but some required sources are still missing:")
        for source_id in missing_required:
            print(f"  - {source_id}")
    else:
        print(f"Source manifest written to {SOURCE_MANIFEST_PATH}")


if __name__ == "__main__":
    main()
