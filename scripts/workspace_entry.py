"""Executable entry point kept separate from the importable package."""

from workspace.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
