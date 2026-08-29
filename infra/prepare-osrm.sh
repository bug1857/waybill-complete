#!/usr/bin/env bash
# Preprocess an OSM extract for OSRM's MLD pipeline.
#
# Three stages, all in the same image: extract applies the routing profile,
# partition builds the multi-level overlay, customize computes cell weights.
# The .osrm* artefacts are gitignored -- they are large and fully regenerable.
set -euo pipefail

EXTRACT="${1:-monaco-latest}"
IMAGE="ghcr.io/project-osrm/osrm-backend:latest"
DATA_DIR="$(cd "$(dirname "$0")/../data/osm" && pwd)"
PBF="${EXTRACT}.osm.pbf"

if [ ! -f "$DATA_DIR/$PBF" ]; then
  echo "error: $DATA_DIR/$PBF not found." >&2
  echo "Download an extract from https://download.geofabrik.de first." >&2
  echo "Use a city or small region -- a whole country needs tens of GB of RAM." >&2
  exit 1
fi

run() { docker run --rm -t -v "$DATA_DIR:/data" "$IMAGE" "$@"; }

echo "==> extract (applying car profile)"
run osrm-extract -p /opt/car.lua "/data/$PBF"
echo "==> partition"
run osrm-partition "/data/${EXTRACT}.osrm"
echo "==> customize"
run osrm-customize "/data/${EXTRACT}.osrm"
echo "==> done. Start the server with: make osrm-up"
