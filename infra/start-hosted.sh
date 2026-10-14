#!/bin/sh
set -eu
# ponytail: one small regional router and one solve slot; workers need a larger plan.
osrm-routed --ip 127.0.0.1 --threads 1 --algorithm mld --max-table-size 100 /app/data/osm/monaco-jaipur-release.osrm &
exec python3 -m api.server --host 0.0.0.0 --port "${PORT:-10000}" \
    --osrm-url http://127.0.0.1:5000 \
    --dataset-id 'monaco-jaipur-261014:3a31b6f8f58812732870d619f7e5de5c34dbc62b15ae4c5d77e10ed797f52b09:osrm-3ac496ff8fd7e1af53846179d73d06a97f719c8ad2217d008ed868942398665c:car:MLD'
