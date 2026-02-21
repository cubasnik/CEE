.PHONY: venv install install-dev test lint run clean

PYTHON := .venv/bin/python
PIP := .venv/bin/pip

venv:
	python3 -m venv .venv

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

run:
	$(PYTHON) -m uvicorn lcm.main:app --reload

clean:
	rm -rf .venv .pytest_cache
