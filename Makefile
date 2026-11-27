.ONESHELL:
ENV_PREFIX=.venv/bin/

.PHONY: clean
clean:            ## cleanup the project structure
	@find . -name '*.pyc' -type f -delete
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@rm -rf .cache
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -rf build
	@rm -rf dist
	@rm -rf src/*.egg-info
	@rm -rf .venv/
	@rm -rf .coverage
	@rm -rf coverage.xml
	@rm -rf htmlcov
	@rm -rf .tox/
	@rm -rf docs/_build

.PHONY: create-venv
create-venv:
	@echo "creating virtual environment ..."
	@rm -rf .venv
	@python3 -m venv .venv
	@./.venv/bin/pip install -U pip
	@./.venv/bin/pip install -e ".[test,lint]"

.PHONY: install
install:          ## Install the project in dev mode.
	$(ENV_PREFIX)pip install -e .[test]


.PHONY: lint
lint:             ## Check linting, formatting and types (same as CI, modifies nothing)
	$(ENV_PREFIX)ruff check src tests scripts --no-fix
	$(ENV_PREFIX)ruff format --check src tests scripts
	$(ENV_PREFIX)mypy src tests scripts

.PHONY: format
format:           ## Apply ruff fixes and formatting
	$(ENV_PREFIX)ruff check src tests scripts --fix
	$(ENV_PREFIX)ruff format src tests scripts

.PHONY: test
test:
	$(ENV_PREFIX)pytest tests --cov=src --cov-report=html

.PHONY: run
run:              ## Start the game server
	$(ENV_PREFIX)track-back-server

.PHONY: openapi
openapi:          ## Regenerate docs/openapi.json
	$(ENV_PREFIX)python -c "import json; from track_back.server.server import Server; print(json.dumps(Server().app.openapi(), indent=2))" > docs/openapi.json