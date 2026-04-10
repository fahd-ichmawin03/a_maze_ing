PYTHON      = python3
MAIN        = a_maze_ing.py
CONFIG      = config.txt
VENV        = .venv
PIP         = $(VENV)/bin/pip
PYTHON_VENV = $(VENV)/bin/python3

.PHONY: all install run debug lint lint-strict clean fclean re build-pkg
all: install
install: $(VENV)/bin/activate

$(VENV)/bin/activate:
	@echo "[install] Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "[install] Upgrading pip..."
	$(PIP) install --upgrade pip -q
	@echo "[install] Installing lint/build tools..."
	$(PIP) install flake8 mypy build -q
	@echo "[install] Building mazegen wheel from source..."
	$(PYTHON_VENV) -m build --wheel --outdir . -q
	@echo "[install] Installing mazegen..."
	$(PIP) install mazegen-*.whl -q
	@echo "[install] Done. Run with: make run"

run: $(VENV)/bin/activate
	$(PYTHON_VENV) $(MAIN) $(CONFIG)

debug: $(VENV)/bin/activate
	$(PYTHON_VENV) -m pdb $(MAIN) $(CONFIG)

lint: $(VENV)/bin/activate
	@echo "[lint] Running flake8..."
	$(VENV)/bin/flake8 . --exclude=$(VENV),dist,build
	@echo "[lint] Running mypy..."
	$(VENV)/bin/mypy . \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs \
		--exclude '$(VENV)|dist|build'
	@echo "[lint] All checks passed."

lint-strict: $(VENV)/bin/activate
	@echo "[lint-strict] Running flake8..."
	$(VENV)/bin/flake8 . --exclude=$(VENV),dist,build
	@echo "[lint-strict] Running mypy --strict..."
	$(VENV)/bin/mypy . --strict \
		--exclude '$(VENV)|dist|build'
	@echo "[lint-strict] All strict checks passed."

build-pkg: $(VENV)/bin/activate
	@echo "[build-pkg] Building wheel and sdist into dist/..."
	$(PYTHON_VENV) -m build
	@echo "[build-pkg] Done."

clean:
	@echo "[clean] Removing caches..."
	find . -type d -name "__pycache__" -not -path "./$(VENV)/*" \
		-exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -not -path "./$(VENV)/*" \
		-exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -not -path "./$(VENV)/*" -delete 2>/dev/null || true
	rm -rf mazegen.egg-info build
	@echo "[clean] Done."

fclean: clean
	@echo "[fclean] Removing venv, dist and wheels..."
	rm -rf $(VENV) dist mazegen-*.whl
	@echo "[fclean] Done."

re: fclean install