# my-python-template

## Description

Template for my python projects.

## Prerequisites
Make sure you have `pip` and `python3` installed on your system. You can check by running on the command line:

```
python3 --version
pip --version
```

## Installation

Clone the repository and install the package using pip:

```
git clone https://github.com/acc-aqt/my-python-template
cd my-python-template
pip install .
```

As `my-python-template` is configured as a GitHub-template you can also use this template by clicking "use this template" on the GitHub page.

## Execution

An exemplary entry point `my-sum` is configured in the 'pyproject.toml'.
Call `my-sum  --help` to check the required arguments.

## Development Setup (if needed)

If you are developing or testing and need to use the source code directly:

- Run `make setup-venv` to create and activate a virtual environment. The python interpreter is located in `.venv/bin/python3`.

- Run `make install` to install the project in develop mode.

- Run `make test` to run the tests.