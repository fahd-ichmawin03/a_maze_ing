"""
mazegen — Reusable maze generation package for A-Maze-ing.

Quick start:
    from mazegen import MazeGenerator

    gen = MazeGenerator(width=20, height=15, seed=42, perfect=True)
    gen.generate()

    for row in gen.to_hex_grid():
        print(row)

    print("Path:", gen.solution_dirs)
"""

from mazegen.maze_generator import (
    MazeGenerator,
    NORTH,
    EAST,
    SOUTH,
    WEST,
    OPPOSITE,
    DELTA,
    DIR_LETTER,
)

__all__ = [
    "MazeGenerator",
    "NORTH",
    "EAST",
    "SOUTH",
    "WEST",
    "OPPOSITE",
    "DELTA",
    "DIR_LETTER",
]

__version__ = "1.0.0"
__author__ = "A-Maze-ing team"
