"""
config_parser.py — Robust configuration parser for A-Maze-ing.

Reads the config.txt file, validates types, maze boundaries,
and ensures entry/exit points are not blocked by the '42' pattern.
"""

import sys
import os
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Set


@dataclass
class MazeConfig:
    """Data structure for maze configuration."""
    width: int
    height: int
    entry: Tuple[int, int]
    exit_: Tuple[int, int]
    output_file: str
    perfect: bool
    seed: Optional[int] = None
    algorithm: str = "recursive_backtracker"
    extra: Dict[str, str] = field(default_factory=dict)


def _compute_42_cells(w: int, h: int) -> Set[Tuple[int, int]]:
    """Computes '42' pattern cells for parsing validation."""
    FOUR = ["101", "101", "111", "001", "001"]
    TWO = ["111", "001", "111", "100", "111"]
    cells: Set[Tuple[int, int]] = set()
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
    """Reads and validates the configuration file."""
    raw: Dict[str, str] = {}

    if not os.path.isfile(path):
        raise FileNotFoundError(f"Configuration file '{path}' not found.")

    try:
        with open(path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    raise ValueError(
                        f"Line {lineno}:'KEY=VALUE' format expected."
                        )

                k_part, _, v_part = line.partition("=")
                key = k_part.strip().upper()
                value = v_part.strip()

                if not key:
                    raise ValueError(
                        f"Line {lineno}: Key is empty before '='."
                        )
                if not value:
                    raise ValueError(
                        f"Line {lineno}: Value for '{key}' is missing."
                        )

                raw[key] = value
    except Exception as e:
        if isinstance(e, ValueError):
            raise e
        raise RuntimeError(f"Error reading file: {e}")

    required = {"WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"}
    missing = required - raw.keys()
    if missing:
        raise ValueError(
            f"Missing configuration parameters: {', '.join(sorted(missing))}"
            )

    def get_int(k: str) -> int:
        try:
            val = int(raw[k])
            if val < 2:
                raise ValueError
            return val
        except ValueError:
            raise ValueError(
                f"'{k}' must be an integer >= 2 (received: '{raw[k]}')."
                )

    def get_coord(k: str) -> Tuple[int, int]:
        parts = raw[k].split(",")
        if len(parts) != 2:
            raise ValueError(
                f"'{k}' must be in x,y format (received: '{raw[k]}')."
                )
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            raise ValueError(f"Coordinates for '{k}' must be integers.")

    def get_bool(k: str) -> bool:
        v = raw[k].lower()
        if v in ("true", "1", "yes", "y"):
            return True
        if v in ("false", "0", "no", "n"):
            return False
        raise ValueError(f"'{k}' must be a boolean (True/False).")

    width = get_int("WIDTH")
    height = get_int("HEIGHT")
    entry = get_coord("ENTRY")
    exit_ = get_coord("EXIT")
    output = raw["OUTPUT_FILE"]
    perfect = get_bool("PERFECT")

    seed = int(
        raw["SEED"]) if "SEED" in raw and raw["SEED"].isdigit() else None
    algo = raw.get("ALGORITHM", "recursive_backtracker")

    if not (0 <= entry[0] < width and 0 <= entry[1] < height):
        raise ValueError(f"ENTRY {entry} is out of bounds ({width}x{height}).")
    if not (0 <= exit_[0] < width and 0 <= exit_[1] < height):
        raise ValueError(f"EXIT {exit_} is out of bounds ({width}x{height}).")
    if entry == exit_:
        raise ValueError("Entry and exit points must be different cells.")

    cells42 = _compute_42_cells(width, height)
    if entry in cells42:
        raise ValueError(
            f"ENTRY {entry} cannot be placed on the '42' pattern."
            )
    if exit_ in cells42:
        raise ValueError(f"EXIT {exit_} cannot be placed on the '42' pattern.")

    known = required | {"SEED", "ALGORITHM"}
    extra = {k: v for k, v in raw.items() if k not in known}

    return MazeConfig(
        width, height, entry, exit_, output, perfect, seed, algo, extra
        )


if __name__ == "__main__":
    try:
        path = sys.argv[1] if len(sys.argv) > 1 else "config.txt"
        config = parse_config(path)
        print(f"[OK] Configuration loaded:\n{config}")
    except Exception as err:
        print(f"[ERROR] {err}", file=sys.stderr)
        sys.exit(1)
