# Repository conventions

## Directory map and responsibilities

| Path | Purpose |
| --- | --- |
| `AGENTS.md` | Repository-wide agent instructions and documentation index |
| `README.md` | User installation, CLI usage, YAML schema, and runtime behavior |
| `docs/` | Focused setup, convention, discovery, and release guides |
| `src/workspace/config.py` | YAML parsing, strict validation, data models, and discovery; independent of iTerm |
| `src/workspace/cli.py` | Argument parsing, init/list/validate, JSON plans, and CLI error reporting |
| `src/workspace/backend.py` | iTerm adapter, session profiles, native splits, and quoted startup input |
| `src/workspace/__init__.py` | Package version |
| `src/workspace/__main__.py` | `python -m workspace` entry point |
| `scripts/workspace_entry.py` | PyInstaller entry point |
| `scripts/build.py` | Native standalone build and isolated executable smoke checks |
| `scripts/package.py` | Versioned archive and checksum generation |
| `scripts/publish_tap.py` | Verify published archives, generate formula, and push the tap update |
| `tests/test_workspace.py` | Configuration, discovery, CLI, and fake iTerm adapter tests |
| `tests/test_releases.py` | Version and formula tests |
| `tests/live_smoke.py` | Explicit live iTerm integration check |
| `examples/` | YAML definitions; `demo.yaml` is the portable, harmless smoke example |
| `.github/workflows/release.yml` | Native arm64/x86_64 builds and tag-triggered release publishing |
| `mise.toml` | Pinned Python and standard project tasks |
| `pyproject.toml` | Package metadata, dependencies, entry point, pytest, and Ruff settings |
| `constraints-build.txt` | Verified dependency pins for setup and builds |

Generated `.venv/`, `build/`, `dist/`, `.release/`, Python caches, and tool caches
are ignored. Do not commit generated binaries, archives, checksums, or PyInstaller
spec files. This repository also ignores `.iterm/` for local workspace definitions;
put shared examples in `examples/`.

## File naming

- Use `snake_case.py` for Python modules and scripts. Keep automated tests named
  `test_*.py`; live checks should remain separate from pytest discovery.
- Use lowercase descriptive names with hyphens for new Markdown guides in
  `docs/` (for example, `development.md` or `release-checklist.md`). Keep the
  conventional root names `README.md` and `AGENTS.md`.
- Prefer `.yaml` for new examples and workspace definitions. Keep `.yml`
  compatibility and `.yaml` precedence. Definition names and path rules are
  documented in [discovery.md](discovery.md).
- Release tags use `vMAJOR.MINOR.PATCH`; archives use
  `workspace-VERSION-macos-ARCH.tar.gz`, where `ARCH` is `arm64` or `x86_64`.
  The tap script supports stable three-component versions only.

## Code and change workflow

Follow the existing small-module design and local style: four-space indentation,
snake_case functions, PascalCase classes, module docstrings, and `pathlib.Path`
for filesystem operations. Keep parsing/data models independent of API calls;
import the iTerm backend only when launching. Use `ConfigError` for invalid user
configuration and let the CLI translate errors into messages and exit codes.

Preserve strict parsing: unknown fields and duplicate YAML keys are errors;
environment values must be strings; pane names must be unique; directories must
exist; only schema version 1 is supported. Layouts are binary split trees limited
to 16 panes and depth 8. Changes to these contracts need docs and regression tests.

Use fake API/session objects for ordinary backend tests. Cover observable behavior
and failure recovery when fixing bugs. Shell construction belongs in the backend
and must quote individual values and entire scripts, including multiline input.
Preserve creation order and window ownership rules in [AGENTS.md](../AGENTS.md).

Inspect the working tree before editing and preserve unrelated work. When creating
a branch, use `codex/` unless the user specifies another name. Keep changes focused,
run the relevant [development checks](development.md), and report any unverified
behavior. Keep documentation aligned with the code: the README owns user-facing
schema/usage, and each guide owns its detailed workflow. Link to those guides from
the root agent index rather than copying lengthy instructions there.

Publishing procedures belong in [releases.md](releases.md). Read that guide before
changing build pins, release automation, version numbers, or tap publishing.
