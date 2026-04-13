VENV = .venv
PY   = $(VENV)/bin/python3
PIP  = $(VENV)/bin/pip

.PHONY: install run debug lint clean

install:
	$(PIP) install -q --upgrade pip
	$(PIP) install -q flake8 mypy build
	$(PY) -m build --wheel --outdir . -q
	$(PIP) install -q mazegen-*.whl

run:
	$(PY) a_maze_ing.py config.txt

debug:
	$(PY) -m pdb a_maze_ing.py config.txt

lint:
	$(VENV)/bin/flake8 . --exclude=$(VENV),build
	$(VENV)/bin/mypy . --ignore-missing-imports --disallow-untyped-defs \
	    --check-untyped-defs --warn-return-any --warn-unused-ignores \
	    --exclude "$(VENV)|build"

clean:
	find . -name "__pycache__" -not -path "./$(VENV)/*" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache build mazegen.egg-info mazegen-*.whl
