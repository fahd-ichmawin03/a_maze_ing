PYTHON = python3
MAIN = a_maze_ing.py
CONFIG = config.txt

all: run

install:
	pip install flake8 mypy

run:
	$(PYTHON) $(MAIN) $(CONFIG)

debug:
	$(PYTHON) -m pdb $(MAIN) $(CONFIG)

clean:
	rm -rf .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +

build:
	python3 -m build
	mv dist/* .
	rm -rf dist

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs

.PHONY: all install run debug clean lint
