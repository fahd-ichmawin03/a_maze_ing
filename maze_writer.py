"""
maze_writer.py — Writes a generated maze to the output file format.

Output format:
    - One hex digit per cell, rows separated by newlines
    - Empty line
    - Entry coordinates  (x,y)
    - Exit  coordinates  (x,y)
    - Shortest path as N/E/S/W letters
    - All lines end with \\n

Usage:
    from maze_writer import write_maze
    write_maze(gen, cfg)
"""

import sys
from mazegen.maze_generator import MazeGenerator
from config_parser import MazeConfig


def write_maze(gen: MazeGenerator, cfg: MazeConfig) -> None:
    """Write the generated maze to the configured output file.

    Args:
        gen: A MazeGenerator instance that has already been generate()d.
        cfg: The parsed MazeConfig holding the output filename.

    Raises:
        RuntimeError: If the generator has not been run yet.
        OSError:      If the file cannot be written.
    """
    hex_rows = gen.to_hex_grid()  # raises RuntimeError if not generated
    ex, ey = gen.entry
    xx, xy = gen.exit_

    try:
        with open(cfg.output_file, "w", encoding="utf-8") as f:
            # Hex grid — one row per line
            for row in hex_rows:
                f.write(row + "\n")

            # Blank separator
            f.write("\n")

            # Entry, exit, shortest path
            f.write(f"{ex},{ey}\n")
            f.write(f"{xx},{xy}\n")
            f.write(gen.solution_dirs + "\n")

    except OSError as e:
        print(f"[ERROR] Cannot write output file '{cfg.output_file}': {e}",
              file=sys.stderr)
        raise