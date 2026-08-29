PY := ./.venv/bin/python

.PHONY: help setup test purity gate clean

help:
	@echo "make setup   - create .venv and install dev dependencies"
	@echo "make test    - run the full test suite"
	@echo "make purity  - check that core/ touches no network, disk, or database"
	@echo "make gate    - verify the current phase's exit gate"

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
