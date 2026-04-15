#!/usr/bin/env bash
# build_tiles.sh — Generate MVT tile directories for the KYV city mod.
#
# Requirements:
#   brew install tippecanoe osmium-tool
#   pip3 install geopandas pyarrow pyogrio shapely
#
# Outputs:
#   build/serve/kyv/tiles/{z}/{x}/{y}.mvt     — main map tiles
#   build/serve/kyv/foundation/{z}/{x}/{y}.mvt — foundation depth tiles

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCES="$ROOT/build/tile-sources"
TILES_DIR="$ROOT/build/serve/kyv/tiles"
FOUNDATION_DIR="$ROOT/build/serve/kyv/foundation"

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------

if ! command -v tippecanoe &>/dev/null; then
  echo "[tiles] ERROR: tippecanoe not found. Run: brew install tippecanoe" >&2
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  echo "[tiles] ERROR: python3 not found." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

echo "[tiles] Creating output directories..."
mkdir -p "$SOURCES" "$TILES_DIR" "$FOUNDATION_DIR"

# ---------------------------------------------------------------------------
# Step 1: Export GeoJSON tile sources from parquet / gzip
# ---------------------------------------------------------------------------

echo "[tiles] Exporting GeoJSON tile sources..."
python3 "$ROOT/scripts/python/build_tile_sources.py"

# Verify required sources
for layer in transportation aeroway buildings building_depth; do
  if [[ ! -f "$SOURCES/$layer.geojson" ]]; then
    echo "[tiles] ERROR: Missing source file: $SOURCES/$layer.geojson" >&2
    exit 1
  fi
done

# ---------------------------------------------------------------------------
# Step 2: Main tiles (transportation, building, aeroway, water)
# ---------------------------------------------------------------------------

echo "[tiles] Building main tiles (z7–z15)..."

MAIN_ARGS=(
  --output-to-directory="$TILES_DIR/"
  --force
  --minimum-zoom=7
  --maximum-zoom=15
  --no-tile-size-limit
  --simplification=4
  --coalesce-densest-as-needed
)

# Always include roads, buildings, aeroways
MAIN_ARGS+=(-L "transportation:$SOURCES/transportation.geojson")
MAIN_ARGS+=(-L "building:$SOURCES/buildings.geojson")
MAIN_ARGS+=(-L "aeroway:$SOURCES/aeroway.geojson")

# Include water if non-empty
if [[ -f "$SOURCES/water.geojson" ]]; then
  water_count=$(python3 -c "
import json
with open('$SOURCES/water.geojson') as f:
    d = json.load(f)
print(len(d.get('features', [])))
")
  if [[ "$water_count" -gt 0 ]]; then
    echo "[tiles]   Including water layer ($water_count features)"
    MAIN_ARGS+=(-L "water:$SOURCES/water.geojson")
  else
    echo "[tiles]   Skipping empty water layer"
  fi
fi

tippecanoe "${MAIN_ARGS[@]}"

# ---------------------------------------------------------------------------
# Step 3: Foundation tiles (building_depth)
# ---------------------------------------------------------------------------

echo "[tiles] Building foundation tiles (z7–z15)..."

tippecanoe \
  --output-to-directory="$FOUNDATION_DIR/" \
  --force \
  --minimum-zoom=7 \
  --maximum-zoom=15 \
  --no-tile-size-limit \
  -L "building_depth:$SOURCES/building_depth.geojson"

# ---------------------------------------------------------------------------
# Step 4: Rename .pbf → .mvt
# ---------------------------------------------------------------------------

echo "[tiles] Renaming .pbf → .mvt ..."

rename_tiles() {
  local dir="$1"
  local count=0
  while IFS= read -r -d '' f; do
    mv "$f" "${f%.pbf}.mvt"
    count=$((count + 1))
  done < <(find "$dir" -name "*.pbf" -print0)
  echo "[tiles]   $dir: renamed $count files"
}

rename_tiles "$TILES_DIR"
rename_tiles "$FOUNDATION_DIR"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

main_count=$(find "$TILES_DIR" -name "*.mvt" | wc -l | tr -d ' ')
foundation_count=$(find "$FOUNDATION_DIR" -name "*.mvt" | wc -l | tr -d ' ')

echo ""
echo "[tiles] ✓ Tile build complete."
echo "[tiles]   Main tiles:       $main_count .mvt files → $TILES_DIR"
echo "[tiles]   Foundation tiles: $foundation_count .mvt files → $FOUNDATION_DIR"
echo ""
echo "[tiles] Next: run scripts/serve.sh in a separate terminal, then launch the game."
