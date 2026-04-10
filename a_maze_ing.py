"""
a_maze_ing.py — Main entry point for the A-Maze-ing maze generator.

Usage:
    python3 a_maze_ing.py config.txt

The program:
    1. Parses the configuration file.
    2. Generates the maze using the chosen algorithm.
    3. Writes the hex-encoded maze + solution to the output file.
    4. Launches the visual renderer (terminal or mlx).
"""

import sys

from config_parser import MazeConfig, parse_config
from maze_writer import write_maze
from maze_renderer import TerminalRenderer
from mazegen.maze_generator import MazeGenerator


def build_generator(cfg: MazeConfig) -> MazeGenerator:
    """Instantiate and run the maze generator from a config.

    Args:
        cfg: Validated MazeConfig object.

    Returns:
        A MazeGenerator that has already been generate()d.
    """
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
    return gen


def main() -> None:
    """Parse args, generate maze, write output, launch renderer."""
    # ------------------------------------------------------------------ #
    # 1. Argument check
    # ------------------------------------------------------------------ #
    if len(sys.argv) != 2:
        print(
            "Usage: python3 a_maze_ing.py <config_file>",
            file=sys.stderr,
        )
        sys.exit(1)

    config_path: str = sys.argv[1]

    # ------------------------------------------------------------------ #
    # 2. Parse configuration
    # ------------------------------------------------------------------ #
    try:
        cfg = parse_config(config_path)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"[ERROR] Invalid configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # 3. Generate maze
    # ------------------------------------------------------------------ #
    try:
        gen = build_generator(cfg)
    except ValueError as e:
        print(f"[ERROR] Maze generation failed: {e}", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # 4. Write output file
    # ------------------------------------------------------------------ #
    try:
        write_maze(gen, cfg)
        print(f"[OK] Maze written to '{cfg.output_file}'.")
    except OSError:
        # Error message already printed by write_maze
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # 5. Launch renderer
    # ------------------------------------------------------------------ #
    if cfg.display == "terminal":
        renderer = TerminalRenderer(gen, cfg)
        renderer.run()
    elif cfg.display == "mlx":
        # MLX renderer (bonus — falls back to terminal if unavailable)
        try:
            from maze_renderer_mlx import MlxRenderer  # type: ignore
            MlxRenderer(gen, cfg).run()
        except ImportError:
            print(
                "[WARN] MLX renderer not available — falling back to terminal.",
                file=sys.stderr,
            )
            TerminalRenderer(gen, cfg).run()
    else:
        print(f"[WARN] Unknown display mode '{cfg.display}'. "
              "Using terminal.", file=sys.stderr)
        TerminalRenderer(gen, cfg).run()


if __name__ == "__main__":
    main()