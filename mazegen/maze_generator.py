"""
maze_generator.py — Reusable maze generation module for A-Maze-ing.

Provides the MazeGenerator class that generates mazes using several
algorithms and exposes the maze structure plus a BFS shortest path.

Wall bit encoding per cell (same as the output file format):
    Bit 0 (LSB) = North
    Bit 1       = East
    Bit 2       = South
    Bit 3       = West
    1 = wall closed, 0 = wall open

Example:
    from mazegen.maze_generator import MazeGenerator

    gen = MazeGenerator(width=20, height=15, seed=42, perfect=True)
    gen.generate()

    grid   = gen.grid          # list[list[int]]  — hex values
    path   = gen.solution      # list[tuple[int,int]]
    dirs   = gen.solution_dirs # str  e.g. "SSEENWW..."
"""

import random
from collections import deque
from typing import Optional


# ---------------------------------------------------------------------------
# Direction constants
# ---------------------------------------------------------------------------

NORTH: int = 0b0001   # bit 0
EAST:  int = 0b0010   # bit 1
SOUTH: int = 0b0100   # bit 2
WEST:  int = 0b1000   # bit 3

OPPOSITE: dict[int, int] = {
    NORTH: SOUTH,
    SOUTH: NORTH,
    EAST:  WEST,
    WEST:  EAST,
}

DELTA: dict[int, tuple[int, int]] = {
    NORTH: (0, -1),
    EAST:  (1,  0),
    SOUTH: (0,  1),
    WEST:  (-1, 0),
}

DIR_LETTER: dict[int, str] = {
    NORTH: "N",
    EAST:  "E",
    SOUTH: "S",
    WEST:  "W",
}


# ---------------------------------------------------------------------------
# Union-Find (for Kruskal)
# ---------------------------------------------------------------------------

class _UnionFind:
    """Simple Union-Find with path compression and union by rank."""

    def __init__(self, n: int) -> None:
        """Initialize with n elements."""
        self._parent: list[int] = list(range(n))
        self._rank: list[int] = [0] * n

    def find(self, x: int) -> int:
        """Find root with path compression."""
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        """Union two sets. Returns True if they were disjoint."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1
        return True


# ---------------------------------------------------------------------------
# MazeGenerator
# ---------------------------------------------------------------------------

class MazeGenerator:
    """Generates a rectangular maze using a chosen algorithm.

    The internal representation is a 2-D grid of integers where each
    integer encodes which walls are *closed* (bit = 1) around that cell.

    Supported algorithms:
        - ``"recursive_backtracker"`` (default) — deep, winding paths.
        - ``"prim"``                            — more uniform, branchy.
        - ``"kruskal"``                         — random spanning tree.

    Args:
        width:     Number of columns (>= 2).
        height:    Number of rows    (>= 2).
        entry:     (x, y) entry cell. Defaults to (0, 0).
        exit_:     (x, y) exit cell.  Defaults to (width-1, height-1).
        perfect:   If True the maze has exactly one path between any two cells.
        seed:      Integer seed for the RNG (None = non-deterministic).
        algorithm: One of ``"recursive_backtracker"``, ``"prim"``,
                   ``"kruskal"``.

    Attributes:
        grid:          2-D list[list[int]] — wall bitmask per cell (row, col).
        solution:      list of (x, y) cells from entry to exit after generate().
        solution_dirs: String of N/E/S/W letters for the solution path.

    Raises:
        ValueError: On invalid parameters.
    """

    ALGORITHMS: frozenset[str] = frozenset(
        {"recursive_backtracker", "prim", "kruskal"}
    )

    def __init__(
        self,
        width: int = 20,
        height: int = 15,
        entry: tuple[int, int] = (0, 0),
        exit_: Optional[tuple[int, int]] = None,
        perfect: bool = True,
        seed: Optional[int] = None,
        algorithm: str = "recursive_backtracker",
    ) -> None:
        """Initialize the maze generator."""
        if width < 2 or height < 2:
            raise ValueError("Width and height must be >= 2.")
        if algorithm not in self.ALGORITHMS:
            raise ValueError(
                f"Unknown algorithm '{algorithm}'. "
                f"Choose from: {', '.join(sorted(self.ALGORITHMS))}."
            )

        self.width: int = width
        self.height: int = height
        self.entry: tuple[int, int] = entry
        self.exit_: tuple[int, int] = exit_ if exit_ is not None else (
            width - 1, height - 1
        )
        self.perfect: bool = perfect
        self.seed: Optional[int] = seed
        self.algorithm: str = algorithm

        self._rng: random.Random = random.Random(seed)

        # Grid: grid[row][col] — all walls closed at init
        self.grid: list[list[int]] = [
            [NORTH | EAST | SOUTH | WEST for _ in range(width)]
            for _ in range(height)
        ]

        self.solution: list[tuple[int, int]] = []
        self.solution_dirs: str = ""
        self._generated: bool = False
        # Set of cells belonging to the "42" pattern
        self._42_cells: set[tuple[int, int]] = set()

        self._validate_coords()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_coords(self) -> None:
        """Check that entry and exit are valid distinct in-bounds cells."""
        for name, (x, y) in (("entry", self.entry), ("exit", self.exit_)):
            if not (0 <= x < self.width and 0 <= y < self.height):
                raise ValueError(
                    f"{name} ({x}, {y}) is outside the maze "
                    f"({self.width}x{self.height})."
                )
        if self.entry == self.exit_:
            raise ValueError("Entry and exit must be different cells.")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate(self) -> "MazeGenerator":
        """Generate the maze in-place.

        Computes the '42' cell set first so the maze algorithm can route
        around them, then runs the chosen algorithm, enforces borders,
        opens entry/exit, fixes coherence, and finds the BFS path.

        Returns:
            self  (allows chaining: gen.generate().solution)
        """
        # Reset
        self.grid = [
            [NORTH | EAST | SOUTH | WEST for _ in range(self.width)]
            for _ in range(self.height)
        ]
        self._42_cells = set()

        # 1. Compute '42' cells (obstacles for the algorithm)
        self._compute_42_cells()

        # 2. Run generation algorithm (treats _42_cells as unvisitable)
        if self.algorithm == "recursive_backtracker":
            self._recursive_backtracker()
        elif self.algorithm == "prim":
            self._prim()
        elif self.algorithm == "kruskal":
            self._kruskal()

        # 3. Close all walls of '42' cells (stamp the pattern)
        for (cx, cy) in self._42_cells:
            self.grid[cy][cx] = NORTH | EAST | SOUTH | WEST

        # 4. Extra openings for non-perfect mazes
        if not self.perfect:
            self._add_extra_openings()

        # 5. Fix borders, entry/exit, coherence
        self._enforce_border_walls()
        self._open_entry_exit()
        self._enforce_coherence()

        # 6. BFS shortest path
        self.solution, self.solution_dirs = self._bfs_shortest_path()
        self._generated = True
        return self

    # ------------------------------------------------------------------
    # "42" pattern — computed BEFORE generation
    # ------------------------------------------------------------------

    def _compute_42_cells(self) -> None:
        """Compute which cells will form the '42' pattern and store them.

        The pattern uses a 5-row × 3-col pixel font for each digit with a
        1-cell gap between them, centred in the maze.

        If the maze is too small the pattern is skipped and a warning is
        printed.
        """
        FOUR: list[str] = [
            "101",
            "101",
            "111",
            "001",
            "001",
        ]
        TWO: list[str] = [
            "111",
            "001",
            "111",
            "100",
            "111",
        ]

        digit_w, digit_h = 3, 5
        gap = 1
        pattern_w = digit_w * 2 + gap
        pattern_h = digit_h

        min_cols = pattern_w + 4
        min_rows = pattern_h + 4
        if self.width < min_cols or self.height < min_rows:
            print(
                "[INFO] Maze is too small to embed the '42' pattern "
                f"(need at least {min_cols}x{min_rows})."
            )
            return

        ox = (self.width - pattern_w) // 2
        oy = (self.height - pattern_h) // 2

        digits: list[list[str]] = [FOUR, TWO]
        for d_idx, digit in enumerate(digits):
            dx_offset = d_idx * (digit_w + gap)
            for row_idx, row in enumerate(digit):
                for col_idx, pixel in enumerate(row):
                    if pixel == "1":
                        cx = ox + dx_offset + col_idx
                        cy = oy + row_idx
                        if self._in_bounds(cx, cy):
                            self._42_cells.add((cx, cy))

        # Make sure entry/exit are not blocked by the pattern
        self._42_cells.discard(self.entry)
        self._42_cells.discard(self.exit_)

    # ------------------------------------------------------------------
    # Wall helpers
    # ------------------------------------------------------------------

    def _remove_wall(self, x: int, y: int, direction: int) -> None:
        """Open the wall between (x, y) and its neighbour in direction.

        Args:
            x:         Column index.
            y:         Row index.
            direction: One of NORTH, EAST, SOUTH, WEST.
        """
        dx, dy = DELTA[direction]
        nx, ny = x + dx, y + dy
        self.grid[y][x] &= ~direction
        self.grid[ny][nx] &= ~OPPOSITE[direction]

    def _has_wall(self, x: int, y: int, direction: int) -> bool:
        """Return True if the wall in direction is closed.

        Args:
            x:         Column index.
            y:         Row index.
            direction: One of NORTH, EAST, SOUTH, WEST.

        Returns:
            True if wall bit is set.
        """
        return bool(self.grid[y][x] & direction)

    def _in_bounds(self, x: int, y: int) -> bool:
        """Return True if (x, y) is inside the grid.

        Args:
            x: Column index.
            y: Row index.

        Returns:
            True if valid.
        """
        return 0 <= x < self.width and 0 <= y < self.height

    def _is_visitable(self, x: int, y: int) -> bool:
        """Return True if a cell can be visited by generation algorithms.

        '42' cells are treated as solid obstacles.

        Args:
            x: Column index.
            y: Row index.

        Returns:
            True if in bounds and not a '42' cell.
        """
        return self._in_bounds(x, y) and (x, y) not in self._42_cells

    def _neighbours(
        self, x: int, y: int, visitable_only: bool = False
    ) -> list[tuple[int, int, int]]:
        """Return in-bounds neighbours as (nx, ny, direction) triples.

        Args:
            x:             Column index.
            y:             Row index.
            visitable_only: If True, exclude '42' cells.

        Returns:
            List of (nx, ny, direction).
        """
        result: list[tuple[int, int, int]] = []
        for direction, (dx, dy) in DELTA.items():
            nx, ny = x + dx, y + dy
            if visitable_only:
                if self._is_visitable(nx, ny):
                    result.append((nx, ny, direction))
            else:
                if self._in_bounds(nx, ny):
                    result.append((nx, ny, direction))
        return result

    # ------------------------------------------------------------------
    # Algorithm: Recursive Backtracker (DFS)
    # ------------------------------------------------------------------

    def _recursive_backtracker(self) -> None:
        """Generate a perfect maze using iterative DFS.

        Skips '42' cells so the algorithm routes around the pattern.
        """
        visited: set[tuple[int, int]] = set()
        sx, sy = self.entry
        # If entry is a '42' cell (shouldn't happen) fall back to (0,0)
        if not self._is_visitable(sx, sy):
            sx, sy = 0, 0
        stack: list[tuple[int, int]] = [(sx, sy)]
        visited.add((sx, sy))

        while stack:
            x, y = stack[-1]
            neighbours = self._neighbours(x, y, visitable_only=True)
            self._rng.shuffle(neighbours)
            moved = False
            for nx, ny, direction in neighbours:
                if (nx, ny) not in visited:
                    self._remove_wall(x, y, direction)
                    visited.add((nx, ny))
                    stack.append((nx, ny))
                    moved = True
                    break
            if not moved:
                stack.pop()

    # ------------------------------------------------------------------
    # Algorithm: Prim's randomised
    # ------------------------------------------------------------------

    def _prim(self) -> None:
        """Generate a perfect maze using randomised Prim's algorithm.

        Skips '42' cells so the algorithm routes around the pattern.
        """
        visited: set[tuple[int, int]] = set()
        sx, sy = self.entry
        if not self._is_visitable(sx, sy):
            sx, sy = 0, 0
        visited.add((sx, sy))

        frontier: list[tuple[int, int, int, int, int]] = []

        def add_frontier(x: int, y: int) -> None:
            for nx, ny, d in self._neighbours(x, y, visitable_only=True):
                if (nx, ny) not in visited:
                    frontier.append((x, y, nx, ny, d))

        add_frontier(sx, sy)

        while frontier:
            idx = self._rng.randrange(len(frontier))
            frontier[idx], frontier[-1] = frontier[-1], frontier[idx]
            x, y, nx, ny, direction = frontier.pop()
            if (nx, ny) in visited:
                continue
            self._remove_wall(x, y, direction)
            visited.add((nx, ny))
            add_frontier(nx, ny)

    # ------------------------------------------------------------------
    # Algorithm: Kruskal's randomised
    # ------------------------------------------------------------------

    def _kruskal(self) -> None:
        """Generate a perfect maze using randomised Kruskal's algorithm.

        '42' cells are excluded from the spanning tree.
        """
        # Only use visitable cells
        cells = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if self._is_visitable(x, y)
        ]
        cell_index: dict[tuple[int, int], int] = {
            cell: idx for idx, cell in enumerate(cells)
        }
        uf = _UnionFind(len(cells))

        walls: list[tuple[int, int, int]] = []
        for x, y in cells:
            if self._is_visitable(x + 1, y):
                walls.append((x, y, EAST))
            if self._is_visitable(x, y + 1):
                walls.append((x, y, SOUTH))

        self._rng.shuffle(walls)

        for x, y, direction in walls:
            dx, dy = DELTA[direction]
            nx, ny = x + dx, y + dy
            ia, ib = cell_index[(x, y)], cell_index[(nx, ny)]
            if uf.union(ia, ib):
                self._remove_wall(x, y, direction)

    # ------------------------------------------------------------------
    # Post-generation helpers
    # ------------------------------------------------------------------

    def _add_extra_openings(self) -> None:
        """Randomly remove extra walls to create loops (non-perfect mode)."""
        extra_count = max(1, (self.width * self.height) // 7)
        opened = 0
        attempts = 0
        while opened < extra_count and attempts < extra_count * 20:
            attempts += 1
            x = self._rng.randrange(self.width)
            y = self._rng.randrange(self.height)
            if (x, y) in self._42_cells:
                continue
            direction = self._rng.choice([NORTH, EAST, SOUTH, WEST])
            dx, dy = DELTA[direction]
            nx, ny = x + dx, y + dy
            if (
                self._in_bounds(nx, ny)
                and (nx, ny) not in self._42_cells
                and self._has_wall(x, y, direction)
            ):
                self._remove_wall(x, y, direction)
                opened += 1

    def _enforce_border_walls(self) -> None:
        """Close all outer-facing walls on the grid border."""
        for x in range(self.width):
            self.grid[0][x] |= NORTH
            self.grid[self.height - 1][x] |= SOUTH
        for y in range(self.height):
            self.grid[y][0] |= WEST
            self.grid[y][self.width - 1] |= EAST

    def _open_entry_exit(self) -> None:
        """Open the outer wall of the entry and exit cells."""
        ex, ey = self.entry
        xx, xy = self.exit_
        for cx, cy in ((ex, ey), (xx, xy)):
            d = self._outer_direction(cx, cy)
            if d is not None:
                self.grid[cy][cx] &= ~d

    def _outer_direction(self, x: int, y: int) -> Optional[int]:
        """Return the direction pointing outside the grid for a border cell.

        Args:
            x: Column.
            y: Row.

        Returns:
            Direction constant or None.
        """
        if y == 0:
            return NORTH
        if y == self.height - 1:
            return SOUTH
        if x == 0:
            return WEST
        if x == self.width - 1:
            return EAST
        return None

    def _enforce_coherence(self) -> None:
        """Ensure wall symmetry between neighbouring non-'42' cells.

        Skips cells in the '42' pattern to preserve their solid appearance.
        """
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) in self._42_cells:
                    continue
                for direction in (EAST, SOUTH):
                    dx, dy = DELTA[direction]
                    nx, ny = x + dx, y + dy
                    if not self._in_bounds(nx, ny):
                        continue
                    if (nx, ny) in self._42_cells:
                        continue
                    a = bool(self.grid[y][x] & direction)
                    b = bool(self.grid[ny][nx] & OPPOSITE[direction])
                    if a != b:
                        self.grid[y][x] |= direction
                        self.grid[ny][nx] |= OPPOSITE[direction]

    # ------------------------------------------------------------------
    # BFS shortest path
    # ------------------------------------------------------------------

    def _bfs_shortest_path(self) -> tuple[list[tuple[int, int]], str]:
        """Find the shortest path from entry to exit using BFS.

        Treats '42' cells as impassable walls.

        Returns:
            (path, dirs) — path as cell list, dirs as N/E/S/W string.

        Raises:
            ValueError: If no path exists.
        """
        start = self.entry
        goal = self.exit_

        queue: deque[tuple[int, int]] = deque([start])
        came_from: dict[
            tuple[int, int],
            Optional[tuple[tuple[int, int], int]]
        ] = {start: None}

        while queue:
            x, y = queue.popleft()
            if (x, y) == goal:
                break
            for nx, ny, direction in self._neighbours(x, y):
                if (nx, ny) in came_from:
                    continue
                if (nx, ny) in self._42_cells:
                    continue
                if not self._has_wall(x, y, direction):
                    came_from[(nx, ny)] = ((x, y), direction)
                    queue.append((nx, ny))

        if goal not in came_from:
            raise ValueError(
                f"No path found from {start} to {goal}. "
                "The maze may be disconnected."
            )

        path: list[tuple[int, int]] = []
        dirs: list[str] = []
        current: tuple[int, int] = goal

        while came_from[current] is not None:
            prev_info = came_from[current]
            assert prev_info is not None
            prev, direction = prev_info
            path.append(current)
            dirs.append(DIR_LETTER[direction])
            current = prev

        path.append(start)
        path.reverse()
        dirs.reverse()
        return path, "".join(dirs)

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def to_hex_grid(self) -> list[str]:
        """Return the maze as a list of hex-encoded row strings.

        Returns:
            List of strings, one per row; each character is a hex digit.

        Raises:
            RuntimeError: If generate() has not been called yet.
        """
        if not self._generated:
            raise RuntimeError("Call generate() before to_hex_grid().")
        return [
            "".join(f"{cell:X}" for cell in row)
            for row in self.grid
        ]

    def cell_walls(self, x: int, y: int) -> dict[str, bool]:
        """Return which walls are closed around a cell.

        Args:
            x: Column index.
            y: Row index.

        Returns:
            Dict with keys 'N', 'E', 'S', 'W' mapped to True/False.

        Raises:
            ValueError:   If (x, y) is out of bounds.
            RuntimeError: If generate() has not been called.
        """
        if not self._generated:
            raise RuntimeError("Call generate() before cell_walls().")
        if not self._in_bounds(x, y):
            raise ValueError(f"Cell ({x}, {y}) is out of bounds.")
        v = self.grid[y][x]
        return {
            "N": bool(v & NORTH),
            "E": bool(v & EAST),
            "S": bool(v & SOUTH),
            "W": bool(v & WEST),
        }

    def __repr__(self) -> str:
        """Return a short string representation."""
        return (
            f"MazeGenerator(width={self.width}, height={self.height}, "
            f"algorithm='{self.algorithm}', perfect={self.perfect}, "
            f"seed={self.seed}, generated={self._generated})"
        )