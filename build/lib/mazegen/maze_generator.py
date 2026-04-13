import random
from collections import deque
from typing import Optional

N, E, S, W = 1, 2, 4, 8
OPP = {N: S, S: N, E: W, W: E}
DX  = {N: 0, E: 1, S: 0, W: -1}
DY  = {N: -1, E: 0, S: 1, W: 0}
DIR_LETTER = {N: "N", E: "E", S: "S", W: "W"}


class MazeGenerator:
    """Generates a maze via recursive backtracker.

    Args:
        width, height: Maze dimensions (>= 2).
        entry, exit_:  (x, y) cell coordinates.
        perfect:       If True, exactly one path between any two cells.
        seed:          RNG seed for reproducibility.

    Attributes:
        grid:          2-D list[list[int]], bitmask per cell (1=wall closed).
        solution:      list of (x, y) from entry to exit.
        solution_dirs: Direction string e.g. "SSEENN...".
        _42_cells:     Set of cells forming the '42' pattern.

    Example::

        gen = MazeGenerator(20, 15, seed=42).generate()
        for row in gen.to_hex_grid():
            print(row)
        print(gen.solution_dirs)
    """

    def __init__(
        self,
        width: int = 20,
        height: int = 15,
        entry: tuple[int, int] = (0, 0),
        exit_: Optional[tuple[int, int]] = None,
        perfect: bool = True,
        seed: Optional[int] = None,
    ) -> None:
        if width < 2 or height < 2:
            raise ValueError("Width and height must be >= 2.")
        self.width = width
        self.height = height
        self.entry = entry
        self.exit_: tuple[int, int] = exit_ if exit_ is not None else (width - 1, height - 1)
        self.perfect = perfect
        self.seed = seed
        self._rng = random.Random(seed)
        self.grid: list[list[int]] = []
        self.solution: list[tuple[int, int]] = []
        self.solution_dirs: str = ""
        self._42_cells: set[tuple[int, int]] = set()

        if not (0 <= entry[0] < width and 0 <= entry[1] < height):
            raise ValueError(f"entry {entry} out of bounds")
        if not (0 <= self.exit_[0] < width and 0 <= self.exit_[1] < height):
            raise ValueError(f"exit {self.exit_} out of bounds")
        if entry == self.exit_:
            raise ValueError("entry and exit must differ")

    def generate(self) -> "MazeGenerator":
        self.grid = [[N | E | S | W] * self.width for _ in range(self.height)]
        self._42_cells = set()
        self._compute_42()
        self._carve()
        for cx, cy in self._42_cells:
            self.grid[cy][cx] = N | E | S | W
        if not self.perfect:
            self._add_loops()
        self._fix_open_areas()
        self._enforce_borders()
        self._open_endpoints()
        self.solution, self.solution_dirs = self._bfs()
        return self

    def _compute_42(self) -> None:
        FOUR = ["101", "101", "111", "001", "001"]
        TWO  = ["111", "001", "111", "100", "111"]
        pw = 7
        if self.width < pw + 4 or self.height < 9:
            print("[INFO] Maze too small for '42' pattern.")
            return
        ox = (self.width - pw) // 2
        oy = (self.height - 5) // 2
        for di, digit in enumerate([FOUR, TWO]):
            for ri, row in enumerate(digit):
                for ci, px in enumerate(row):
                    if px == "1":
                        cx, cy = ox + di * 4 + ci, oy + ri
                        if 0 <= cx < self.width and 0 <= cy < self.height:
                            self._42_cells.add((cx, cy))
        self._42_cells.discard(self.entry)
        self._42_cells.discard(self.exit_)

    def _ok(self, x: int, y: int) -> bool:
        return (0 <= x < self.width and 0 <= y < self.height
                and (x, y) not in self._42_cells)

    def _carve(self) -> None:
        vis = [[False] * self.width for _ in range(self.height)]
        sx, sy = self.entry
        stack = [(sx, sy)]
        vis[sy][sx] = True
        while stack:
            x, y = stack[-1]
            dirs = [N, E, S, W]
            self._rng.shuffle(dirs)
            moved = False
            for d in dirs:
                nx, ny = x + DX[d], y + DY[d]
                if self._ok(nx, ny) and not vis[ny][nx]:
                    self.grid[y][x] &= ~d
                    self.grid[ny][nx] &= ~OPP[d]
                    vis[ny][nx] = True
                    stack.append((nx, ny))
                    moved = True
                    break
            if not moved:
                stack.pop()

    def _add_loops(self) -> None:
        count = max(1, self.width * self.height // 7)
        done = attempts = 0
        while done < count and attempts < count * 20:
            attempts += 1
            x = self._rng.randrange(self.width)
            y = self._rng.randrange(self.height)
            if (x, y) in self._42_cells:
                continue
            d = self._rng.choice([N, E, S, W])
            nx, ny = x + DX[d], y + DY[d]
            if self._ok(nx, ny) and (self.grid[y][x] & d):
                self.grid[y][x] &= ~d
                self.grid[ny][nx] &= ~OPP[d]
                done += 1

    def _is_3x3_open(self, x: int, y: int) -> bool:
        for row in range(y, y + 3):
            for col in range(x, x + 2):
                if self.grid[row][col] & E:
                    return False
        for row in range(y, y + 2):
            for col in range(x, x + 3):
                if self.grid[row][col] & S:
                    return False
        return True

    def _fix_open_areas(self) -> None:
        changed = True
        while changed:
            changed = False
            for y in range(self.height - 2):
                for x in range(self.width - 2):
                    if self._is_3x3_open(x, y):
                        self.grid[y + 1][x + 1] |= E
                        self.grid[y + 1][x + 2] |= W
                        changed = True

    def _enforce_borders(self) -> None:
        for x in range(self.width):
            self.grid[0][x] |= N
            self.grid[self.height - 1][x] |= S
        for y in range(self.height):
            self.grid[y][0] |= W
            self.grid[y][self.width - 1] |= E

    def _open_endpoints(self) -> None:
        for cx, cy in (self.entry, self.exit_):
            if cy == 0:
                self.grid[cy][cx] &= ~N
            elif cy == self.height - 1:
                self.grid[cy][cx] &= ~S
            elif cx == 0:
                self.grid[cy][cx] &= ~W
            else:
                self.grid[cy][cx] &= ~E

    def _bfs(self) -> tuple[list[tuple[int, int]], str]:
        sx, sy = self.entry
        ex, ey = self.exit_
        prev: dict[tuple[int, int], Optional[tuple[tuple[int, int], int]]] = {(sx, sy): None}
        q: deque[tuple[int, int]] = deque([(sx, sy)])
        while q:
            x, y = q.popleft()
            if (x, y) == (ex, ey):
                break
            for d in [N, E, S, W]:
                nx, ny = x + DX[d], y + DY[d]
                nk = (nx, ny)
                if (0 <= nx < self.width and 0 <= ny < self.height
                        and nk not in prev
                        and nk not in self._42_cells
                        and not (self.grid[y][x] & d)):
                    prev[nk] = ((x, y), d)
                    q.append((nx, ny))
        if (ex, ey) not in prev:
            raise ValueError(f"No path from {self.entry} to {self.exit_}.")
        path: list[tuple[int, int]] = []
        dirs: list[str] = []
        cur: tuple[int, int] = (ex, ey)
        while prev[cur] is not None:
            info = prev[cur]
            assert info is not None
            p, d = info
            path.append(cur)
            dirs.append(DIR_LETTER[d])
            cur = p
        path.append((sx, sy))
        path.reverse()
        dirs.reverse()
        return path, "".join(dirs)

    def to_hex_grid(self) -> list[str]:
        return ["".join(f"{c:X}" for c in row) for row in self.grid]

    def cell_walls(self, x: int, y: int) -> dict[str, bool]:
        v = self.grid[y][x]
        return {"N": bool(v & N), "E": bool(v & E), "S": bool(v & S), "W": bool(v & W)}