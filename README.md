*This project has been created as part of the 42 curriculum by wamansou, fichmawi.*

# A-Maze-ing

## Description

A-Maze-ing is a maze generator written in Python 3. It generates a random rectangular maze from a configuration file, writes it to an output file using a hexadecimal wall encoding, and displays it interactively in the terminal.

Key features:
- Perfect or imperfect maze generation (configurable)
- Reproducible output via a seed
- Embedded **"42" pattern** made of fully-closed cells, visible in the terminal rendering
- Shortest path computation (BFS) from entry to exit
- Interactive terminal display: regenerate, show/hide solution, change colour palette
- Reusable `mazegen` package installable via `pip`

---

## Instructions

### Requirements

- Python 3.10 or later
- `make` (GNU Make)

### Installation

```bash
make install
```

installs all dependencies.

### Run

```bash
make run
# or directly:
.venv/bin/python3 a_maze_ing.py config.txt
```

### Debug

```bash
make debug
```

### Lint

```bash
make lint
```

### Clean

```bash
make clean
```

---

## Configuration file

The program takes a single argument: a plain text configuration file.
Each line must follow the `KEY=VALUE` format. Lines starting with `#` are ignored.

### Mandatory keys

| Key           | Description                          | Example              |
|---------------|--------------------------------------|----------------------|
| `WIDTH`       | Number of columns (≥ 2)              | `WIDTH=20`           |
| `HEIGHT`      | Number of rows (≥ 2)                 | `HEIGHT=15`          |
| `ENTRY`       | Entry cell coordinates `x,y`         | `ENTRY=0,0`          |
| `EXIT`        | Exit cell coordinates `x,y`          | `EXIT=19,14`         |
| `OUTPUT_FILE` | Path of the output file              | `OUTPUT_FILE=maze.txt` |
| `PERFECT`     | Perfect maze? (`True` / `False`)     | `PERFECT=True`       |

### Optional keys

| Key        | Description                        | Example       |
|------------|------------------------------------|---------------|
| `SEED`     | Integer seed for reproducibility   | `SEED=42`     |

### Constraints

- `ENTRY` and `EXIT` must be different cells inside the maze bounds.
- Neither `ENTRY` nor `EXIT` may fall on a cell belonging to the "42" pattern.

### Example `config.txt`

```
# A-Maze-ing default config
WIDTH=20
HEIGHT=15
ENTRY=0,0
EXIT=19,14
OUTPUT_FILE=maze.txt
PERFECT=True
SEED=42
```

---

## Output file format

- One hexadecimal digit per cell, rows separated by newlines.
- Each digit encodes closed walls as a 4-bit mask: bit 0 = North, bit 1 = East, bit 2 = South, bit 3 = West (1 = closed).
- After a blank line: entry coordinates, exit coordinates, shortest path as a sequence of `N` / `E` / `S` / `W` letters.

```
A9579551539553915553
...

0,0
19,14
SSEENNEESS...
```

---

## Maze generation algorithm

The project uses the **recursive backtracker** (iterative DFS).

### How it works

1. Start from the entry cell, mark it visited, push it onto a stack.
2. While the stack is not empty, look at the top cell and pick a random unvisited neighbour (skipping "42" cells).
3. Remove the wall between them, mark the neighbour visited, push it.
4. If no unvisited neighbours exist, pop the stack (backtrack).
5. After the DFS, stamp the "42" cells as fully closed, enforce border walls, and open the entry/exit outer wall.
6. Run a post-pass to break any 3×3 open areas by closing one wall.
7. Compute the shortest path with BFS.

### Why this algorithm

The recursive backtracker was chosen for three reasons:

- **Simplicity**: the logic fits in a single function with no external data structures beyond a stack and a visited set.
- **Quality**: it produces long, winding corridors with relatively few dead-ends, which makes the maze visually interesting and challenging to solve.
- **Compatibility**: starting the DFS from the entry cell guarantees that the entry is always connected to the rest of the maze before any post-processing.

---

## Reusable module — `mazegen`

The maze generation logic is packaged as a standalone pip-installable module located at the root of the repository.

### Install

```bash
pip install mazegen-1.0.0-py3-none-any.whl
# or from source:
pip install .
```

### Usage

```python
from mazegen import MazeGenerator

# Basic usage
gen = MazeGenerator(width=20, height=15, seed=42, perfect=True).generate()

# Hex grid (list of strings, one per row)
for row in gen.to_hex_grid():
    print(row)

# Shortest path as direction string
print(gen.solution_dirs)   # e.g. "SSEENNWW..."

# Shortest path as list of (x, y) cells
print(gen.solution)

# Walls around a specific cell
print(gen.cell_walls(3, 2))  # {'N': True, 'E': False, 'S': True, 'W': False}

# Set of cells forming the '42' pattern
print(gen._42_cells)
```

### Custom parameters

| Parameter  | Type              | Default             | Description                     |
|------------|-------------------|---------------------|---------------------------------|
| `width`    | `int`             | `20`                | Number of columns (≥ 2)         |
| `height`   | `int`             | `15`                | Number of rows (≥ 2)            |
| `entry`    | `tuple[int, int]` | `(0, 0)`            | Entry cell                      |
| `exit_`    | `tuple[int, int]` | `(width-1, height-1)` | Exit cell                     |
| `perfect`  | `bool`            | `True`              | Single path between any 2 cells |
| `seed`     | `int \| None`     | `None`              | RNG seed                        |

### Rebuild the package

```bash
python -m pip install build
python -m build          # produces mazegen-1.0.0-py3-none-any.whl in dist/
```

---

## Team & project management

### Roles

| Member     | Role                                                              |
|------------|-------------------------------------------------------------------|
| `fichmawi` | Maze generation algorithm, output file format, BFS path finder    |
| `wamansou` | Config parser, terminal renderer, Makefile                        |

### Planning

We initially planned to implement three generation algorithms (DFS, Prim, Kruskal) and a graphical display with MiniLibX. After the first week we realised the complexity of managing multiple algorithms while keeping the code clean, and decided to focus on a single well-tested algorithm with a polished terminal renderer. The "42" pattern and the open-area constraint took more time than expected to get right.

### What worked well

- Separating the generator into its own `mazegen` package early made testing much easier.
- Using a seed from the start saved a lot of debugging time (reproducible bugs).
- The BFS path finder required no changes once written.

### What could be improved

- The open-area fix is a post-processing pass; a better approach would be to prevent 3×3 areas from forming during the DFS itself.

### Tools used

- **Python 3.12**, **flake8**, **mypy** for code quality

---

## Resources

- [Maze generation algorithms — Wikipedia](https://en.wikipedia.org/wiki/Maze_generation_algorithm)
- [BFS shortest path — cp-algorithms.com](https://cp-algorithms.com/graph/breadth-first-search.html)
- [Python `random` module documentation](https://docs.python.org/3/library/random.html)

### AI usage

We used AI during this project for the following tasks:

- **Debugging**: AI helped diagnose the 3×3 open-area bug and suggested the post-processing scan approach.
