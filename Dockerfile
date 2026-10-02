FROM ghcr.io/project-osrm/osrm-backend@sha256:3ac496ff8fd7e1af53846179d73d06a97f719c8ad2217d008ed868942398665c

RUN apt-get update && apt-get install -y --no-install-recommends python3 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN mkdir -p data/osm \
    && curl --fail --location --retry 3 https://download.geofabrik.de/europe/monaco-260901.osm.pbf -o data/osm/monaco-release.osm.pbf \
    && echo 'f2d904ee0aa156a2252c39c0ab80ca7b3fafb28da6a84b909084a26f068ac962  data/osm/monaco-release.osm.pbf' | sha256sum -c - \
    && osrm-extract -t 1 -p /opt/car.lua data/osm/monaco-release.osm.pbf \
    && osrm-partition -t 1 data/osm/monaco-release.osrm \
    && osrm-customize -t 1 data/osm/monaco-release.osrm
COPY core core
COPY adapters adapters
COPY bench bench
COPY api api
COPY web web
COPY data/live data/live
COPY infra/start-hosted.sh infra/start-hosted.sh
ENV PYTHONUNBUFFERED=1
EXPOSE 10000
CMD ["sh", "/app/infra/start-hosted.sh"]
