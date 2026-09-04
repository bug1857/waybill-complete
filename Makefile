PY := ./.venv/bin/python
OSRM_PORT ?= 5001

.PHONY: help setup test purity gate clean osrm-prepare osrm-up osrm-down osrm-status web-setup web-dev web-build crosscheck

help:
	@echo "make setup   - create .venv and install dev dependencies"
	@echo "make test    - run the full test suite"
	@echo "make purity  - check that core/ touches no network, disk, or database"
	@echo "make gate    - verify the current phase's exit gate"
	@echo ""
	@echo "make osrm-prepare - preprocess the OSM extract (once, ~1 min for Monaco)"
	@echo "make osrm-up      - start the local routing server on :$(OSRM_PORT)"
	@echo "make osrm-down    - stop it"
	@echo "make osrm-status  - is it answering?"
	@echo ""
	@echo "make web-setup    - install web dependencies"
	@echo "make web-dev      - run the web app"
	@echo "make crosscheck   - verify the TS engine agrees with the verified data"

setup:
	python3 -m venv .venv
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet -e ".[dev]"

test:
	$(PY) -m pytest

purity:
	$(PY) -m tools.check_purity

gate: purity
	@echo
	$(PY) -m tools.verify_gate

clean:
	rm -rf .pytest_cache **/__pycache__ .venv

osrm-prepare:
	./infra/prepare-osrm.sh $(or $(EXTRACT),monaco-latest)

osrm-up:
	OSRM_PORT=$(OSRM_PORT) docker compose -f infra/docker-compose.yml up -d
	@echo "waiting for OSRM to answer..."
	@for i in $$(seq 1 30); do \
		curl -sf "http://127.0.0.1:$(OSRM_PORT)/route/v1/driving/7.42,43.73;7.43,43.74" >/dev/null 2>&1 && \
		{ echo "OSRM up on :$(OSRM_PORT)"; exit 0; }; \
		sleep 1; \
	done; \
	echo "OSRM did not answer in 30s; check: docker logs waybill-osrm"; exit 1

osrm-down:
	docker compose -f infra/docker-compose.yml down

osrm-status:
	@curl -sf "http://127.0.0.1:$(OSRM_PORT)/route/v1/driving/7.42,43.73;7.43,43.74" >/dev/null 2>&1 \
		&& echo "OSRM: up" || echo "OSRM: down"

web-setup:
	cd web && npm install

web-dev:
	cd web && npm run dev

web-build:
	cd web && npm run build

# The generated instance data must stay derived from data/tsplib/.
web-data:
	$(PY) -m tools.generate_web_data

# Two independent engines on the same verified data. Python parses the published
# optimal tours; TypeScript scores them. Neither side supplies its own input.
crosscheck: web-data
	@$(PY) -c "import json; from bench.tsplib.parser import parse_tour; \
	  open('.crosscheck-tours.json','w').write(json.dumps({n: list(parse_tour(f'data/tsplib/{n}.opt.tour')) for n in ['eil51','berlin52','st70']}))"
	@cd web && npx tsx scripts/crosscheck.ts ../.crosscheck-tours.json
	@rm -f .crosscheck-tours.json
