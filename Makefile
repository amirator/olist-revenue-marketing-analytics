all:
	python run.py
setup:
	python -m venv .venv && .venv/bin/pip install -r requirements.txt
test:
	python -m pytest -q
