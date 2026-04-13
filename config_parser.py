import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class MazeConfig:
    width: int
    height: int
    entry: tuple[int, int]
    exit_: tuple[int, int]
    output_file: str
    perfect: bool
    seed: Optional[int] = None


def _compute_42_cells(w: int, h: int) -> set[tuple[int, int]]:
    FOUR = ["101", "101", "111", "001", "001"]
    TWO  = ["111", "001", "111", "100", "111"]
    cells: set[tuple[int, int]] = set()
    if w < 11 or h < 9:
        return cells
    ox, oy = (w - 7) // 2, (h - 5) // 2
    for di, digit in enumerate([FOUR, TWO]):
        for ri, row in enumerate(digit):
            for ci, px in enumerate(row):
                if px == "1":
                    cx, cy = ox + di * 4 + ci, oy + ri
                    if 0 <= cx < w and 0 <= cy < h:
                        cells.add((cx, cy))
    return cells


def parse_config(path: str) -> MazeConfig:
    raw: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    raise ValueError(f"Line {lineno}: expected KEY=VALUE")
                k, _, v = line.partition("=")
                raw[k.strip().upper()] = v.strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: '{path}'")

    required = {"WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"}
    missing = required - raw.keys()
    if missing:
        raise ValueError(f"Missing keys: {', '.join(sorted(missing))}")

    def parse_int(k: str) -> int:
        try:
            v = int(raw[k])
        except ValueError:
            raise ValueError(f"{k} must be an integer")
        if v < 2:
            raise ValueError(f"{k} must be >= 2")
        return v

    def parse_coord(k: str) -> tuple[int, int]:
        parts = raw[k].split(",")
        if len(parts) != 2:
            raise ValueError(f"{k}: expected x,y")
        try:
            x, y = int(parts[0]), int(parts[1])
        except ValueError:
            raise ValueError(f"{k}: coordinates must be integers")
        return x, y

    def parse_bool(k: str) -> bool:
        v = raw[k].lower()
        if v in ("true", "1", "yes"):
            return True
        if v in ("false", "0", "no"):
            return False
        raise ValueError(f"{k} must be True or False")

    width  = parse_int("WIDTH")
    height = parse_int("HEIGHT")
    entry  = parse_coord("ENTRY")
    exit_  = parse_coord("EXIT")
    output = raw["OUTPUT_FILE"]
    perfect = parse_bool("PERFECT")
    seed: Optional[int] = None
    if "SEED" in raw:
        try:
            seed = int(raw["SEED"])
        except ValueError:
            raise ValueError("SEED must be an integer")

    if not output:
        raise ValueError("OUTPUT_FILE must not be empty")
    if not (0 <= entry[0] < width and 0 <= entry[1] < height):
        raise ValueError(f"ENTRY {entry} is outside the maze bounds")
    if not (0 <= exit_[0] < width and 0 <= exit_[1] < height):
        raise ValueError(f"EXIT {exit_} is outside the maze bounds")
    if entry == exit_:
        raise ValueError("ENTRY and EXIT must be different cells")

    cells42 = _compute_42_cells(width, height)
    if entry in cells42:
        raise ValueError(f"ENTRY {entry} falls on the '42' pattern")
    if exit_ in cells42:
        raise ValueError(f"EXIT {exit_} falls on the '42' pattern")

    return MazeConfig(width, height, entry, exit_, output, perfect, seed)


if __name__ == "__main__":
    try:
        cfg = parse_config(sys.argv[1] if len(sys.argv) > 1 else "config.txt")
        print(cfg)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)