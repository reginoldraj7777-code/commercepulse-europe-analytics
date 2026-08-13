.PHONY: setup generate-ci generate-full quality analyze notebook warehouse dbt-build test lint validate all clean

PYTHON ?= python
PROFILE ?= ci

setup:
	$(PYTHON) -m pip install -e ".[dev]"

generate-ci:
	$(PYTHON) -m commercepulse.cli generate --profile ci --output data/sample

generate-full:
	$(PYTHON) -m commercepulse.cli generate --profile portfolio --output data/full

quality:
	$(PYTHON) -m commercepulse.cli quality --input data/sample --output artifacts/validation

analyze:
	$(PYTHON) -m commercepulse.cli analyze --input data/sample/clean --output artifacts/analysis

notebook:
	$(PYTHON) scripts/build_notebook.py
	$(PYTHON) scripts/execute_notebook.py notebooks/commercepulse_decision_analysis.ipynb

warehouse:
	docker compose up -d postgres
	$(PYTHON) -m commercepulse.cli load-postgres --input data/sample/clean

dbt-build:
	dbt build --project-dir dbt --profiles-dir dbt

test:
	$(PYTHON) -m pytest

lint:
	ruff check src tests scripts
	sqlfluff lint dbt/models
	sqlfluff lint sql/analysis --templater raw

validate:
	$(PYTHON) scripts/validate_project.py

all: generate-ci quality analyze notebook test validate

clean:
	$(PYTHON) scripts/clean_generated.py
