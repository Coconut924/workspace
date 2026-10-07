# Agent guide

Read `~/AGENTS.md` first for shared instructions. This file applies throughout
this repository.

## Project

`iterm-workspace` is a Python CLI, exposed as `workspace`, that creates native
iTerm2 windows from YAML definitions. Development uses a mise-managed Python
and a local `.venv`; distribution uses standalone macOS executables and Homebrew.

## Start here

- [Development setup and verification](docs/development.md): dependencies,
  commands, test selection, and integration checks.
- [Repository conventions](docs/conventions.md): directory map, file naming,
  module responsibilities, and change workflow.
- [Definition names and directory traversal](docs/discovery.md): discovery
  precedence, Git boundaries, explicit paths, and relative path resolution.
- [Build and publish a release](docs/releases.md): version changes, native
  packaging, GitHub Actions, and publishing the Homebrew formula.
- [User guide and YAML schema](README.md): supported CLI usage and configuration.

## Required practices

- Use the tasks in [mise.toml](mise.toml) and project-local dependencies. Do not
  install global tools without express permission. Keep dependency changes in
  sync with [pyproject.toml](pyproject.toml) and
  [constraints-build.txt](constraints-build.txt); see the release guide before
  changing build pins.
- Preserve module boundaries: offline discovery and validation in `config.py`,
  argument handling in `cli.py`, and iTerm API operations in `backend.py`.
  Validation and dry runs must work without connecting to iTerm.
- Preserve strict YAML validation and the discovery rules in
  [docs/discovery.md](docs/discovery.md). Add regression coverage for changes to
  these behaviors.
- Create a new tab in the current window by default, or a new window with
  `--new-window` (also when no current window exists). Keep profile changes
  session-local. Validate profiles before creation, complete the layout before
  sending startup input, close only the new tab/window on layout/title failure,
  and preserve it if sending startup input fails.
- Quote shell paths, environment values, and entire startup scripts with
  `shlex.quote`. `--no-commands` must still apply directories and environment.
  Avoid logging or sharing resolved secrets from dry-run output.
- For code changes, run `mise run test` and `mise run lint`. Use the additional
  checks in [docs/development.md](docs/development.md) when changing integration
  or packaging. Report checks that could not run and why.
- Keep versions identical in `pyproject.toml` and `src/workspace/__init__.py`.
  Follow [docs/releases.md](docs/releases.md) for publishing; verify both native
  archives and their checksums before updating the tap. Do not replace published
  assets or alter other formulas in the shared tap.
- Update the relevant docs and examples when behavior or workflows change.
  Keep this file as an index and put detailed guidance in `docs/`.
