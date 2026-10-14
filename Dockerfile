FROM ghcr.io/project-osrm/osrm-backend@sha256:3ac496ff8fd7e1af53846179d73d06a97f719c8ad2217d008ed868942398665c

RUN apt-get update && apt-get install -y --no-install-recommends python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY data/roads/monaco-jaipur-release.osm.pbf data/osm/monaco-jaipur-release.osm.pbf
RUN echo '3a31b6f8f58812732870d619f7e5de5c34dbc62b15ae4c5d77e10ed797f52b09  data/osm/monaco-jaipur-release.osm.pbf' | sha256sum -c - \
    && osrm-extract -t 1 -p /opt/car.lua data/osm/monaco-jaipur-release.osm.pbf \
    && osrm-partition -t 1 data/osm/monaco-jaipur-release.osrm \
    && osrm-customize -t 1 data/osm/monaco-jaipur-release.osrm
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
