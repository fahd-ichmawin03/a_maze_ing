"""
config_parser.py — Configuration file parser for A-Maze-ing.

Parses a KEY=VALUE config file and returns a validated MazeConfig object.

Usage:
    from config_parser import parse_config
    cfg = parse_config("config.txt")
    print(cfg.width, cfg.height)
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Supported values
# ---------------------------------------------------------------------------

VALID_ALGORITHMS = {"recursive_backtracker", "prim", "kruskal"}
VALID_DISPLAY_MODES = {"terminal", "mlx"}

MANDATORY_KEYS = {"WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"}


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class MazeConfig:
    """Holds all validated configuration values for the maze generator.

    Attributes:
        width: Number of columns in the maze (>= 2).
        height: Number of rows in the maze (>= 2).
        entry: (x, y) entry cell coordinates.
        exit_: (x, y) exit cell coordinates.
        output_file: Path to the output file.
        perfect: Whether to generate a perfect maze.
        seed: Random seed for reproducibility.
        algorithm: Generation algorithm name.
        display: Display mode ('terminal' or 'mlx').
    """

    width: int
    height: int
    entry: tuple[int, int]
    exit_: tuple[int, int]
    output_file: str
    perfect: bool
    seed: Optional[int] = None
    algorithm: str = "recursive_backtracker"
    display: str = "terminal"
    extra: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_bool(value: str, key: str) -> bool:
    """Parse a boolean string value.

    Args:
        value: Raw string from the config file.
        key: Key name (used in error messages).

    Returns:
        True or False.

    Raises:
        ValueError: If the value is not a recognised boolean string.
    """
    normalised = value.strip().lower()
    if normalised in {"true", "1", "yes"}:
        return True
    if normalised in {"false", "0", "no"}:
        return False
    raise ValueError(
        f"Invalid boolean value for '{key}': '{value}'. "
        "Expected True/False, yes/no, or 1/0."
    )


def _parse_int(value: str, key: str) -> int:
    """Parse a strictly positive integer string value.

    Args:
        value: Raw string from the config file.
        key: Key name (used in error messages).

    Returns:
        Parsed integer.

    Raises:
        ValueError: If the value is not a valid positive integer.
    """
    try:
        result = int(value.strip())
    except ValueError:
        raise ValueError(
            f"Invalid integer value for '{key}': '{value}'."
        )
    if result <= 0:
        raise ValueError(
            f"Value for '{key}' must be a positive integer, got {result}."
        )
    return result


def _parse_coords(value: str, key: str) -> tuple[int, int]:
    """Parse a 'x,y' coordinate pair.

    Args:
        value: Raw string from the config file (e.g. '0,0' or '19,14').
        key: Key name (used in error messages).

    Returns:
        (x, y) tuple of non-negative integers.

    Raises:
        ValueError: If the format is invalid.
    """
    parts = value.strip().split(",")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid coordinate format for '{key}': '{value}'. "
            "Expected 'x,y'."
        )
    try:
        x, y = int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        raise ValueError(
            f"Coordinates for '{key}' must be integers, got '{value}'."
        )
    if x < 0 or y < 0:
        raise ValueError(
            f"Coordinates for '{key}' must be non-negative, got ({x}, {y})."
        )
    return (x, y)


def _read_raw_config(path: str) -> dict[str, str]:
    """Read and parse the raw KEY=VALUE pairs from a config file.

    Comments (lines starting with '#') and blank lines are ignored.

    Args:
        path: Path to the configuration file.

    Returns:
        Dictionary mapping upper-case keys to their raw string values.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If a line has invalid syntax.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Configuration file not found: '{path}'."
        )

    raw: dict[str, str] = {}

    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()

            # Skip blank lines and comments
            if not stripped or stripped.startswith("#"):
                continue

            if "=" not in stripped:
                raise ValueError(
                    f"Syntax error at line {lineno}: "
                    f"expected 'KEY=VALUE', got '{stripped}'."
                )

            key, _, value = stripped.partition("=")
            key = key.strip().upper()
            value = value.strip()

            if not key:
                raise ValueError(
                    f"Empty key at line {lineno}."
                )

            raw[key] = value

    return raw


def _check_mandatory(raw: dict[str, str]) -> None:
    """Ensure all mandatory keys are present.

    Args:
        raw: Dictionary of raw config values.

    Raises:
        ValueError: If one or more mandatory keys are missing.
    """
    missing = MANDATORY_KEYS - raw.keys()
    if missing:
        raise ValueError(
            f"Missing mandatory key(s) in config: {', '.join(sorted(missing))}."
        )


def _validate_bounds(cfg: MazeConfig) -> None:
    """Check that dimensions are large enough and coordinates are in bounds.

    Args:
        cfg: Partially-built MazeConfig object.

    Raises:
        ValueError: On any constraint violation.
    """
    if cfg.width < 2:
        raise ValueError(f"WIDTH must be >= 2, got {cfg.width}.")
    if cfg.height < 2:
        raise ValueError(f"HEIGHT must be >= 2, got {cfg.height}.")

    for name, coord in (("ENTRY", cfg.entry), ("EXIT", cfg.exit_)):
        x, y = coord
        if x >= cfg.width or y >= cfg.height:
            raise ValueError(
                f"{name} ({x}, {y}) is outside maze bounds "
                f"({cfg.width}x{cfg.height})."
            )

    if cfg.entry == cfg.exit_:
        raise ValueError(
            f"ENTRY and EXIT must be different cells, both are {cfg.entry}."
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_config(path: str) -> MazeConfig:
    """Parse and validate a maze configuration file.

    Args:
        path: Path to the .txt configuration file.

    Returns:
        A fully validated MazeConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If any value is invalid or a mandatory key is missing.
        SystemExit: Never — callers should catch exceptions and handle them.
    """
    raw = _read_raw_config(path)
    _check_mandatory(raw)

    # --- Mandatory fields ---
    width = _parse_int(raw["WIDTH"], "WIDTH")
    height = _parse_int(raw["HEIGHT"], "HEIGHT")
    entry = _parse_coords(raw["ENTRY"], "ENTRY")
    exit_ = _parse_coords(raw["EXIT"], "EXIT")
    output_file = raw["OUTPUT_FILE"].strip()
    perfect = _parse_bool(raw["PERFECT"], "PERFECT")

    if not output_file:
        raise ValueError("OUTPUT_FILE must not be empty.")

    # --- Optional fields ---
    known_keys = MANDATORY_KEYS | {"SEED", "ALGORITHM", "DISPLAY"}
    extra: dict[str, str] = {}

    seed: Optional[int] = None
    if "SEED" in raw:
        try:
            seed = int(raw["SEED"].strip())
        except ValueError:
            raise ValueError(
                f"Invalid integer value for 'SEED': '{raw['SEED']}'."
            )

    algorithm = "recursive_backtracker"
    if "ALGORITHM" in raw:
        algorithm = raw["ALGORITHM"].strip().lower()
        if algorithm not in VALID_ALGORITHMS:
            raise ValueError(
                f"Unknown algorithm '{algorithm}'. "
                f"Valid choices: {', '.join(sorted(VALID_ALGORITHMS))}."
            )

    display = "terminal"
    if "DISPLAY" in raw:
        display = raw["DISPLAY"].strip().lower()
        if display not in VALID_DISPLAY_MODES:
            raise ValueError(
                f"Unknown display mode '{display}'. "
                f"Valid choices: {', '.join(sorted(VALID_DISPLAY_MODES))}."
            )

    # Collect unknown keys into extra (non-fatal)
    for key, value in raw.items():
        if key not in known_keys:
            extra[key] = value

    cfg = MazeConfig(
        width=width,
        height=height,
        entry=entry,
        exit_=exit_,
        output_file=output_file,
        perfect=perfect,
        seed=seed,
        algorithm=algorithm,
        display=display,
        extra=extra,
    )

    _validate_bounds(cfg)

    return cfg


# ---------------------------------------------------------------------------
# CLI helper — print parsed config for quick inspection
# ---------------------------------------------------------------------------

def _print_config(cfg: MazeConfig) -> None:
    """Pretty-print a MazeConfig to stdout.

    Args:
        cfg: The parsed configuration object.
    """
    print("=== Parsed MazeConfig ===")
    print(f"  Width         : {cfg.width}")
    print(f"  Height        : {cfg.height}")
    print(f"  Entry         : {cfg.entry}")
    print(f"  Exit          : {cfg.exit_}")
    print(f"  Output file   : {cfg.output_file}")
    print(f"  Perfect       : {cfg.perfect}")
    print(f"  Seed          : {cfg.seed}")
    print(f"  Algorithm     : {cfg.algorithm}")
    print(f"  Display       : {cfg.display}")
    if cfg.extra:
        print(f"  Extra keys    : {cfg.extra}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 config_parser.py <config_file>", file=sys.stderr)
        sys.exit(1)

    try:
        config = parse_config(sys.argv[1])
        _print_config(config)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)