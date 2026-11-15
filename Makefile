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
lint: ## Run linters (optionally specify LINT_PATH=<path>)
	@LINT_TARGET=$(LINT_PATH); \
	if [ -z "$$LINT_TARGET" ]; then LINT_TARGET=src; fi; \
	echo "Running isort..."; \
	$(ENV_PREFIX)isort $$LINT_TARGET; \
	echo "Running docstrfmt..."; \
	$(ENV_PREFIX)docstrfmt $$LINT_TARGET; \
	echo "Running black..."; \
	$(ENV_PREFIX)black $$LINT_TARGET; \
	echo "Running ruff format..."; \
	$(ENV_PREFIX)ruff format $$LINT_TARGET; \
	echo "Running ruff check..."; \
	$(ENV_PREFIX)ruff check $$LINT_TARGET; \
	echo "Running mypy..."; \
	$(ENV_PREFIX)mypy $$LINT_TARGET; \
	echo "Running pylint..."; \
	$(ENV_PREFIX)pylint $$LINT_TARGET

.PHONY: test
test:
	$(ENV_PREFIX)pytest tests --cov=src --cov-report=html

.PHONY: run
run:              ## Start the game server
	$(ENV_PREFIX)track-back-server

.PHONY: openapi
openapi:          ## Regenerate docs/openapi.json
	$(ENV_PREFIX)python -c "import json; from server.server import Server; print(json.dumps(Server().app.openapi(), indent=2))" > docs/openapi.json