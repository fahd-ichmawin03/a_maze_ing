import sys
from mazegen.maze_generator import MazeGenerator
from config_parser import MazeConfig


def write_maze(gen: MazeGenerator, cfg: MazeConfig) -> None:
    ex, ey = gen.entry
    xx, xy = gen.exit_
    try:
        with open(cfg.output_file, "w", encoding="utf-8") as f:
            for row in gen.to_hex_grid():
                f.write(row + "\n")
            f.write("\n")
            f.write(f"{ex},{ey}\n")
            f.write(f"{xx},{xy}\n")
            f.write(gen.solution_dirs + "\n")
    except OSError as e:
        print(f"[ERROR] Cannot write '{cfg.output_file}': {e}", file=sys.stderr)
        raise