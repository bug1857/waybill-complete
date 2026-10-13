PY := ./.venv/bin/python
OSRM_PORT ?= 5001

.PHONY: help setup test purity data gate osrm-gate evidence release-evidence live clean osrm-prepare osrm-up osrm-down osrm-status web-data prototype-crosscheck

help:
	@echo "make setup   - create .venv and install dev dependencies"
	@echo "make test    - run the full test suite"
	@echo "make purity  - check that core/ touches no network, disk, or database"
	@echo "make data    - verify all benchmark-input SHA-256 manifests"
	@echo "make gate    - verify the current phase's exit gate"
	@echo "make osrm-gate - also verify the optional local OSRM integration"
	@echo "make evidence - regenerate the validated bundle, report, and static demo data"
	@echo "make live    - serve the live API and route map on 127.0.0.1:8000"
	@echo ""
	@echo "make osrm-prepare - preprocess the OSM extract (once, ~1 min for Monaco)"
	@echo "make osrm-up      - start the local routing server on :$(OSRM_PORT)"
	@echo "make osrm-down    - stop it"
	@echo "make osrm-status  - is it answering?"
	@echo ""
	@echo "make release-evidence - generate evidence from clean committed source"

setup:
	python3 -m venv .venv
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet -e ".[dev]"

test:
	$(PY) -m pytest

purity:
	$(PY) -m tools.check_purity

data:
	$(PY) -m tools.verify_data_manifest

gate: purity data evidence
	@echo
	$(PY) -m tools.verify_gate

osrm-gate: purity data evidence
	@echo
	$(PY) -m tools.verify_gate --osrm

evidence:
	$(PY) -m tools.generate_evidence

release-evidence:
	$(PY) -m tools.generate_evidence --release

live:
	$(PY) -m api.server

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

# The generated instance data must stay derived from data/tsplib/.
web-data:
	$(PY) -m tools.generate_web_data

# Two independent engines on the same verified data. Python parses the published
# optimal tours; TypeScript scores them. Neither side supplies its own input.
prototype-crosscheck: web-data
	@$(PY) -c "import json; from bench.tsplib.parser import parse_tour; \
	  open('.crosscheck-tours.json','w').write(json.dumps({n: list(parse_tour(f'data/tsplib/{n}.opt.tour')) for n in ['eil51','berlin52','st70']}))"
	@cd reference/google-ui && npx tsx scripts/crosscheck.ts ../../.crosscheck-tours.json
	@rm -f .crosscheck-tours.json
