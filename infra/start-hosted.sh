#!/bin/sh
set -eu
# ponytail: one small regional router and one solve slot; workers need a larger plan.
osrm-routed --ip 127.0.0.1 --threads 1 --algorithm mld --max-table-size 100 /app/data/osm/monaco-release.osrm &
exec python3 -m api.server --host 0.0.0.0 --port "${PORT:-10000}" \
    --osrm-url http://127.0.0.1:5000 \
    --dataset-id 'monaco-260901:f2d904ee0aa156a2252c39c0ab80ca7b3fafb28da6a84b909084a26f068ac962:osrm-3ac496ff8fd7e1af53846179d73d06a97f719c8ad2217d008ed868942398665c:car:MLD'
