# Development setup and verification

## Current setup

The distribution name is `iterm-workspace`; the Python package and CLI are named
`workspace`. The package supports Python 3.11+, while
[mise.toml](../mise.toml) pins development/build Python to 3.12.15.
[pyproject.toml](../pyproject.toml) defines the dependencies and entry point;
[constraints-build.txt](../constraints-build.txt) pins the verified dependency
versions installed by the setup task. Runtime dependencies are PyYAML and iterm2;
development adds pytest, Ruff, and PyInstaller.

Launching and standalone builds require macOS. Enable iTerm2 **Settings →
General → Magic → Enable Python API**, and approve its connection prompt for
live checks. Offline parsing, validation, and unit tests do not require a live
iTerm connection.

## Install locally

Run these commands from the repository root with mise available:

```sh
mise install
mise run setup
.venv/bin/workspace --help
```

Setup creates `.venv` and installs the project in editable mode with development
dependencies and build constraints. Use `.venv/bin/workspace` directly, or
activate `.venv` to use `workspace` on PATH. Source changes take effect in this
editable install; an existing standalone binary must be rebuilt.

Use mise for project dependencies. Shared instructions in `~/AGENTS.md` require
express permission before installing global dependencies with Homebrew.

## Routine checks

```sh
mise run test
mise run lint
.venv/bin/workspace validate examples/demo.yaml
.venv/bin/workspace examples/demo.yaml --dry-run
```

The test task runs pytest over `tests/`; lint runs Ruff over `src`, `tests`, and
`scripts`. Ruff's configured line length is 100; no separate formatter or type
checker task is configured. Dry runs print resolved environment values and
startup scripts, so use the harmless demo rather than private definitions when
sharing output.

For focused debugging, invoke pytest directly, for example:

```sh
.venv/bin/python -m pytest tests/test_workspace.py -k discovery
.venv/bin/python -m pytest tests/test_releases.py
```

`test_workspace.py` covers schema validation, traversal boundaries, CLI behavior,
shell quoting, layout creation, and failure handling with fake iTerm sessions.
`test_releases.py` checks version consistency and Homebrew formula generation.
Use temporary directories and an isolated home for discovery tests; avoid
depending on an agent's actual `~/.iterm` definitions.

## Checks for integration and packaging changes

For iTerm adapter changes, run the live smoke check when API access is available:

```sh
.venv/bin/python tests/live_smoke.py
```

It opens a demo, checks geometry, labels, colors, directories, and output, then
closes only the window it created. It is separate from the normal pytest suite.

For build, dependency, entry-point, or packaging changes:

```sh
mise run build
dist/workspace --help
mise run package
```

The build script checks version consistency and smoke-tests the executable
outside the checkout with a system-only PATH. Packaging invokes the build again
and creates a native archive plus checksum. Test both architectures through the
release workflow before publishing. See [the release guide](releases.md) for
the full process, including live verification of the standalone binary.

For documentation-only edits, verify relative links and command examples against
the checked-in code and tasks. No new tests or binary rebuild are needed.
