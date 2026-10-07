"""Command-line interface."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, Pane, config_dir, definitions, discover, load

TEMPLATE = """version: 1
name: Development
tab_color: "#4779b8"
root: .
shell: /bin/zsh
layout:
  direction: horizontal
  first:
    direction: vertical
    first:
      name: shell
      color: "#182230"
    second:
      name: logs
      color: "#291c20"
      # command: tail -f app.log
  second:
    name: server
    color: "#17251d"
    # command: ./start-server.sh
"""


def plan(config, no_commands=False):
    def node(value):
        if isinstance(value, Pane):
            return {
                "name": value.name,
                "cwd": str(value.cwd),
                "profile": value.profile,
                "color": value.color,
                "env": value.env,
                "command": None if no_commands else value.command,
            }
        return {
            "direction": value.direction,
            "first": node(value.first),
            "second": node(value.second),
        }

    return {
        "name": config.name,
        "source": str(config.source),
        "root": str(config.root),
        "shell": config.shell,
        "tab_color": config.tab_color,
        "layout": node(config.layout),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Launch declarative native iTerm2 workspaces")
    parser.add_argument(
        "target", nargs="?", help="definition name, YAML path, directory, or . (auto-discover)"
    )
    parser.add_argument("argument", nargs="?", help="target for validate/init")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--config-dir", type=Path, default=config_dir(),
        help="fallback definition directory (default: ~/.iterm)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print resolved JSON without opening iTerm"
    )
    parser.add_argument(
        "--no-commands", action="store_true", help="set up panes without startup commands"
    )
    args = parser.parse_args(argv)
    try:
        if args.target == "list":
            if args.argument:
                raise ConfigError("list takes no argument")
            for name, path in sorted(definitions(directory=args.config_dir).items()):
                print(f"{name}\t{path}")
            return 0
        if args.target == "init":
            directory = Path(args.argument or ".").expanduser().resolve()
            if not directory.is_dir():
                raise ConfigError(f"Directory does not exist: {directory}")
            folder = directory / ".iterm"
            folder.mkdir(exist_ok=True)
            path = folder / "default.yaml"
            if (folder / "default.yml").exists():
                raise ConfigError(f"Refusing to overwrite {folder / 'default.yml'}")
            try:
                with path.open("x") as file:
                    file.write(TEMPLATE)
            except FileExistsError:
                raise ConfigError(f"Refusing to overwrite {path}") from None
            print(f"Created {path}; edit commands and colors, then run workspace .")
            return 0
        target = args.argument if args.target == "validate" else args.target
        if args.argument and args.target != "validate":
            raise ConfigError("Unexpected extra argument")
        config = load(discover(target, directory=args.config_dir.expanduser()))
        if args.dry_run:
            print(json.dumps(plan(config, args.no_commands), indent=2))
        elif args.target == "validate":
            print(f"Valid: {config.name} ({len(config.panes)} panes) — {config.source}")
        else:
            from .backend import launch

            launch(config, args.no_commands)
            print(f"Opened {config.name} ({len(config.panes)} panes)")
        return 0
    except (ConfigError, OSError) as exc:
        print(f"workspace: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("workspace: cancelled", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 -- report third-party API errors at the CLI boundary
        print(
            f"workspace: iTerm launch failed: {exc}\n"
            "Enable iTerm Settings > General > Magic > Enable Python API; "
            "approve the connection prompt. Press Ctrl-C to cancel a pending connection.",
            file=sys.stderr,
        )
        return 1
