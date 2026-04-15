#!/usr/bin/env bash
# serve.sh — Start the local HTTP server for KYV city mod assets.
#
# Serves build/serve/ at http://127.0.0.1:8080
# Required before launching Subway Builder with this mod active.
#
# Usage:
#   bash scripts/serve.sh
#
# Verify (in another terminal):
#   curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/kyv/data/demand_data.json.gz

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVE_DIR="$ROOT/build/serve"
HOST="127.0.0.1"
PORT=8080

if [[ ! -d "$SERVE_DIR/kyv" ]]; then
  echo "[serve] ERROR: $SERVE_DIR/kyv does not exist." >&2
  echo "[serve] Run scripts/build_tiles.sh first." >&2
  exit 1
fi

# Quick pre-flight: check required data files exist
for f in demand_data.json.gz buildings_index.json.gz roads.geojson.gz runways_taxiways.geojson.gz; do
  if [[ ! -f "$SERVE_DIR/kyv/data/$f" ]]; then
    echo "[serve] WARNING: Missing city data file: kyv/data/$f" >&2
  fi
done

main_count=$(find "$SERVE_DIR/kyv/tiles/" -name "*.mvt" 2>/dev/null | wc -l | tr -d ' ')
foundation_count=$(find "$SERVE_DIR/kyv/foundation/" -name "*.mvt" 2>/dev/null | wc -l | tr -d ' ')

echo "[serve] Serving $SERVE_DIR at http://$HOST:$PORT"
echo "[serve]   Tiles:      $main_count .mvt files"
echo "[serve]   Foundation: $foundation_count .mvt files"
echo "[serve] Press Ctrl+C to stop."
echo ""

python3 -m http.server "$PORT" --bind "$HOST" --directory "$SERVE_DIR"
