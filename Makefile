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

.PHONY: setup-venv
setup-venv: create-venv
	@echo "activating virtual environment ..."
	@. .venv/bin/activate

.PHONY: install
install:          ## Install the project in dev mode.
	@echo "Don't forget to run 'make setup-venv' if you got errors."
	$(ENV_PREFIX)pip install -e .[test]


.PHONY: lint
lint: ## Run linters (optionally specify PATH=<path>)
	@PATH_TO_LINT=$(PATH); \
	if [ -z "$$PATH_TO_LINT" ]; then PATH_TO_LINT=.; fi; \
	echo "Running isort..."; \
	$(ENV_PREFIX)isort $$PATH_TO_LINT; \
	echo "Running docstrfmt..."; \
	$(ENV_PREFIX)docstrfmt $$PATH_TO_LINT; \
	echo "Running black..."; \
	$(ENV_PREFIX)black $$PATH_TO_LINT; \
	echo "Running ruff format..."; \
	$(ENV_PREFIX)ruff format $$PATH_TO_LINT; \
	echo "Running ruff check..."; \
	$(ENV_PREFIX)ruff check $$PATH_TO_LINT; \
	echo "Running mypy..."; \
	$(ENV_PREFIX)mypy $$PATH_TO_LINT; \
	echo "Running pylint..."; \
	$(ENV_PREFIX)pylint $$PATH_TO_LINT

.PHONY: test
test:
	$(ENV_PREFIX)pytest tests --cov=src --cov-report=html

run:              ## Run main.py
	$(ENV_PREFIX)python src/main.py