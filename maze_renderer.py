"""
maze_renderer.py — Terminal ASCII renderer for A-Maze-ing.

Renders the maze in colour using ANSI escape codes.
Provides an interactive menu:
    1. Re-generate a new maze
    2. Show / hide the solution path
    3. Rotate wall colour palette
    4. Quit

Usage:
    from maze_renderer import TerminalRenderer
    renderer = TerminalRenderer(gen, cfg)
    renderer.run()
"""

import os
import sys
from typing import Optional

from mazegen.maze_generator import (
    MazeGenerator,
    NORTH, EAST, SOUTH, WEST,
)
from config_parser import MazeConfig


# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------

RESET = "\033[0m"


def _ansi_bg(r: int, g: int, b: int) -> str:
    """Return ANSI 24-bit background colour escape sequence."""
    return f"\033[48;2;{r};{g};{b}m"


def _ansi_fg(r: int, g: int, b: int) -> str:
    """Return ANSI 24-bit foreground colour escape sequence."""
    return f"\033[38;2;{r};{g};{b}m"


# Predefined wall colour palettes  (wall_bg, passage_bg)
PALETTES: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = [
    ((40,  40,  40),  (0,   0,   0)),    # default: dark grey / black
    ((180, 120,  30),  (20,  10,   0)),   # gold / dark-brown
    ((20,  100, 180),  (0,   20,  60)),   # blue / navy
    ((30,  140,  60),  (0,   30,  10)),   # green / dark-green
    ((160,  30,  30),  (40,   0,   0)),   # red / dark-red
]

# Colours for special cells
ENTRY_BG:   tuple[int, int, int] = (200,  50, 200)   # magenta
EXIT_BG:    tuple[int, int, int] = (200,  50,  50)   # red
PATH_BG:    tuple[int, int, int] = (30,  180, 200)   # cyan
CELLS42_BG: tuple[int, int, int] = (80,   80,  80)   # medium grey

# Cell display size (width × height in terminal characters)
CELL_W = 2
CELL_H = 1


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class TerminalRenderer:
    """Interactive terminal renderer for a maze.

    Args:
        gen: A MazeGenerator instance (already generated).
        cfg: The parsed MazeConfig.
    """

    def __init__(self, gen: MazeGenerator, cfg: MazeConfig) -> None:
        """Initialise the renderer."""
        self._gen: MazeGenerator = gen
        self._cfg: MazeConfig = cfg
        self._show_path: bool = False
        self._palette_idx: int = 0

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the interactive render loop."""
        self._render()
        while True:
            self._print_menu()
            choice = input("Choice (1-4): ").strip()
            if choice == "1":
                self._regenerate()
            elif choice == "2":
                self._show_path = not self._show_path
                self._render()
            elif choice == "3":
                self._palette_idx = (self._palette_idx + 1) % len(PALETTES)
                self._render()
            elif choice == "4":
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _regenerate(self) -> None:
        """Generate a fresh maze (new random seed) and redisplay."""
        import random
        new_seed = random.randint(0, 2**31)
        self._gen = MazeGenerator(
            width=self._cfg.width,
            height=self._cfg.height,
            entry=self._cfg.entry,
            exit_=self._cfg.exit_,
            perfect=self._cfg.perfect,
            seed=new_seed,
            algorithm=self._cfg.algorithm,
        )
        self._gen.generate()
        self._show_path = False
        self._render()

    def _render(self) -> None:
        """Clear the screen and draw the maze."""
        os.system("clear" if os.name != "nt" else "cls")

        gen = self._gen
        wall_color, passage_color = PALETTES[self._palette_idx]

        path_set: set[tuple[int, int]] = (
            set(gen.solution) if self._show_path else set()
        )

        # Build display: each cell is CELL_H rows × CELL_W cols of spaces
        # We also draw vertical walls (right edge of each cell) and
        # horizontal walls (bottom edge) using half-block characters.

        # We render the maze as a grid of "big pixels":
        # For each cell (x, y) we print CELL_W coloured characters.
        # Between rows we print a separator row showing horizontal walls.

        lines: list[str] = []

        for y in range(gen.height):
            # --- Cell row ---
            cell_line = ""
            for x in range(gen.width):
                bg = self._cell_bg(x, y, path_set, passage_color)
                cell_line += _ansi_bg(*bg) + " " * CELL_W
                # Right wall
                if x < gen.width - 1:
                    if gen.grid[y][x] & EAST:
                        cell_line += _ansi_bg(*wall_color) + " "
                    else:
                        cell_line += _ansi_bg(*bg) + " "
            cell_line += RESET
            lines.append(cell_line)

            # --- Horizontal wall row (below current row) ---
            if y < gen.height - 1:
                wall_line = ""
                for x in range(gen.width):
                    if gen.grid[y][x] & SOUTH:
                        wall_line += _ansi_bg(*wall_color) + " " * CELL_W
                    else:
                        bg = self._cell_bg(x, y, path_set, passage_color)
                        wall_line += _ansi_bg(*bg) + " " * CELL_W
                    # Corner pixel
                    if x < gen.width - 1:
                        wall_line += _ansi_bg(*wall_color) + " "
                wall_line += RESET
                lines.append(wall_line)

        print("\n".join(lines))

    def _cell_bg(
        self,
        x: int,
        y: int,
        path_set: set[tuple[int, int]],
        passage_color: tuple[int, int, int],
    ) -> tuple[int, int, int]:
        """Return the background colour for a given cell.

        Args:
            x:             Column.
            y:             Row.
            path_set:      Set of cells on the solution path.
            passage_color: Default passage background.

        Returns:
            (r, g, b) tuple.
        """
        gen = self._gen
        if (x, y) == gen.entry:
            return ENTRY_BG
        if (x, y) == gen.exit_:
            return EXIT_BG
        if (x, y) in gen._42_cells:
            return CELLS42_BG
        if (x, y) in path_set:
            return PATH_BG
        return passage_color

    def _print_menu(self) -> None:
        """Print the interactive menu."""
        path_label = "Hide path" if self._show_path else "Show path"
        print(
            f"\n==== A-Maze-ing ====\n"
            f"  1. Re-generate a new maze\n"
            f"  2. {path_label}\n"
            f"  3. Change wall colour\n"
            f"  4. Quit"
        )


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from config_parser import parse_config
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.txt"
    try:
        cfg = parse_config(cfg_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    gen = MazeGenerator(
        width=cfg.width,
        height=cfg.height,
        entry=cfg.entry,
        exit_=cfg.exit_,
        perfect=cfg.perfect,
        seed=cfg.seed,
        algorithm=cfg.algorithm,
    )
    gen.generate()
    TerminalRenderer(gen, cfg).run()