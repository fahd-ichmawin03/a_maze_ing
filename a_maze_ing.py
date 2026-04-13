import sys
from config_parser import parse_config
from maze_writer import write_maze
from maze_renderer import TerminalRenderer
from mazegen.maze_generator import MazeGenerator


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py <config>", file=sys.stderr)
        sys.exit(1)

    try:
        cfg = parse_config(sys.argv[1])
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    try:
        gen = MazeGenerator(
            cfg.width, cfg.height, cfg.entry, cfg.exit_,
            cfg.perfect, cfg.seed,
        ).generate()
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    try:
        write_maze(gen, cfg)
        print(f"[OK] Maze written to '{cfg.output_file}'.")
    except OSError:
        sys.exit(1)

    TerminalRenderer(gen, cfg).run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exsciting the maze game !")
