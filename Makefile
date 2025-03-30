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
	@./.venv/bin/pip install -e .[test]

.PHONY: setup-venv
setup-venv: create-venv
	@echo "activating virtual environment ..."
	@. .venv/bin/activate

.PHONY: lint
lint:             ## Run linters
	$(ENV_PREFIX)flake8 src/ tests/
	$(ENV_PREFIX)black src/ tests/
	$(ENV_PREFIX)mypy src/ tests/
	$(ENV_PREFIX)pylint src/ tests/

.PHONY: install
install:          ## Install the project in dev mode.
	@echo "Don't forget to run 'make setup-venv' if you got errors."
	$(ENV_PREFIX)pip install -e .[test]

.PHONY: test
test:       ## Run tests and generate coverage report.
	$(ENV_PREFIX)set -e; \
	$(ENV_PREFIX)pytest -v --cov=src/ --tb=short --maxfail=1 tests/
	$(ENV_PREFIX)coverage xml
	$(ENV_PREFIX)coverage html

.PHONY: bandit
bandit:        ## find common security issues in Python code
	$(ENV_PREFIX)bandit -r src/