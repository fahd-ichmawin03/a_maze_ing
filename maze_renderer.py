import os
import random
from mazegen.maze_generator import MazeGenerator, S, W
from config_parser import MazeConfig
from maze_writer import write_maze

RST = "\033[0m"


def _fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


def _bg(r: int, g: int, b: int) -> str:
    return f"\033[48;2;{r};{g};{b}m"


PALETTES: list[tuple[tuple[int, int, int], tuple[int, int, int], str]] = [
    ((220, 220, 220), (25,  25,  25),  "Default"),
    ((180, 120,  30), (20,  10,   0),  "Amber"),
    ((30,  140, 200), (0,   20,  50),  "Ocean"),
    ((60,  180,  80), (0,   25,  10),  "Forest"),
    ((200,  60,  60), (30,   0,   0),  "Red"),
]

C_ENTRY = (127, 119, 221)
C_EXIT = (216,  90,  48)
C_PATH = (29,  158, 117)
C_42 = (70,   70,  70)


class TerminalRenderer:
    def __init__(self, gen: MazeGenerator, cfg: MazeConfig) -> None:
        self._gen = gen
        self._cfg = cfg
        self._show_path = False
        self._pal = 0
        self._local_rng = random.Random(cfg.seed)

    def run(self) -> None:
        self._render()
        while True:
            self._menu()
            choice = input("Choice (1-4): ").strip()
            if choice == "1":
                self._regenerate()
            elif choice == "2":
                self._show_path = not self._show_path
                self._render()
            elif choice == "3":
                self._pal = (self._pal + 1) % len(PALETTES)
                self._render()
            elif choice == "4":
                print("Bye!")
                break
            else:
                print("  Enter 1, 2, 3 or 4.")

    def _regenerate(self) -> None:
        next_seed = self._local_rng.randint(0, 2**31 - 1)

        self._gen = MazeGenerator(
            self._cfg.width,
            self._cfg.height,
            self._cfg.entry,
            self._cfg.exit_,
            self._cfg.perfect,
            next_seed
        ).generate()
        write_maze(self._gen, self._cfg)
        self._render()

    def _render(self) -> None:
        os.system("clear" if os.name != "nt" else "cls")
        gen = self._gen
        W2, H = gen.width, gen.height
        wall_col, pass_col, pal_name = PALETTES[self._pal]
        path_set: set[tuple[int, int]] = set(
            gen.solution) if self._show_path else set()
        wf = _fg(*wall_col)
        lines: list[str] = []

        for y in range(H + 1):
            sep = ""
            for x in range(W2 + 1):
                sep += wf + "+"
                if x < W2:
                    has_wall = (
                        y == 0 or y == H
                        or bool(gen.grid[y - 1][x] & S if y > 0 else True)
                    )
                    sep += wf + ("──" if has_wall else "  ")
            lines.append(sep + RST)

            if y == H:
                break

            row_line = ""
            for x in range(W2):
                has_left = x == 0 or bool(gen.grid[y][x] & W)
                row_line += wf + ("│" if has_left else " ")
                row_line += self._cell(x, y, path_set, pass_col)
            row_line += wf + "│"
            lines.append(row_line + RST)

        print("\n".join(lines))
        steps = f"| {len(gen.solution)-1} steps" if self._show_path else ""
        print(f"\n  {pal_name} | {W2}×{H} | {steps}")

        if not gen._42_cells:
            print("[NOTICE] Maze is too small to", end="")
            print("display the '42' pattern at the center.")

    def _cell(
        self,
        x: int, y: int,
        path_set: set[tuple[int, int]],
        pass_col: tuple[int, int, int],
    ) -> str:
        gen = self._gen
        if (x, y) == gen.entry:
            return _bg(*C_ENTRY) + "En" + RST
        if (x, y) == gen.exit_:
            return _bg(*C_EXIT) + "Ex" + RST
        if (x, y) in gen._42_cells:
            return _bg(*C_42) + "  " + RST

        # Le chemin est tracé avec des points clairs '•'
        if (x, y) in path_set:
            return _bg(*pass_col) + _fg(*C_PATH) + " •" + RST

        return _bg(*pass_col) + "  " + RST

    def _menu(self) -> None:
        lbl = "Hide solution" if self._show_path else "Show solution"
        print(
            f"\n  ==== A-Maze-ing ====\n"
            f"  1. New maze\n"
            f"  2. {lbl}\n"
            f"  3. Next color palette\n"
            f"  4. Quit"
        )
