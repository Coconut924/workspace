# Definition names and directory traversal

These rules describe [config.py](../src/workspace/config.py). Preserve them when
changing discovery; regression coverage lives in
[test_workspace.py](../tests/test_workspace.py).

## Names and extensions

Definitions live in a project's `.iterm/` directory or in `~/.iterm/` for home
definitions. The default name is `default`. Named lookup accepts letters, digits,
underscores, and hyphens (`[A-Za-z0-9_-]+`). Prefer lowercase descriptive names for
new examples. `init`, `list`, and `validate` are CLI commands; launch definitions
with those names using an explicit YAML path.

Both `.yaml` and `.yml` work. In each directory, `.yaml` wins when both extensions
exist for the same name. `workspace init` writes `.iterm/default.yaml` and refuses
to overwrite either an existing `default.yaml` or `default.yml`.

## Automatic traversal

For no target, `.`, or a bare definition name:

1. Resolve the current directory and walk upward, starting in that directory.
2. Select the nearest directory containing a `.iterm/` directory, then stop
   walking, even if that directory lacks the requested definition.
3. If a `.git` entry is encountered first, stop at that repository root. Check
   its `.iterm/` before stopping. A `.git` file counts too, supporting worktrees.
4. Look for `NAME.yaml`, then `NAME.yml`, in the selected project directory.
5. Fall back to the home definition directory. `--config-dir` replaces this
   fallback; it does not replace project discovery.

If no Git root or project `.iterm/` is found, traversal reaches the filesystem
root before using the fallback. Never continue to another parent `.iterm/`
after selecting the nearest one, and never traverse beyond a Git boundary.

For example, from `project/src/package/`, with a `.git` entry in `project/`:

```text
project/
  .git
  .iterm/dev.yaml
  src/
    .iterm/default.yaml
    package/                 # current directory
```

`workspace dev` selects `project/src/.iterm/`, finds no `dev` there, and tries
`~/.iterm/dev.yaml` (then `.yml`). It does not use `project/.iterm/dev.yaml`.

`workspace list` uses the same directories and precedence. It lists their
immediate YAML files, merges names with project definitions winning over home
definitions, and prints names in sorted order. It does not recurse into nested
definition directories.

## Explicit paths

A target is an explicit path if it is absolute, contains `/`, or has a `.yaml`
or `.yml` suffix. Expand `~` and resolve relative targets from the current
directory. Explicit targets never fall back to home definitions.

| Invocation | Resolution |
| --- | --- |
| `workspace` or `workspace .` | Discover `default` using traversal and fallback |
| `workspace dev` | Discover `dev` using traversal and fallback |
| `workspace file.yaml` | Use that file in the current directory |
| `workspace ./path/file.yaml` | Use exactly that file |
| `workspace ./project/` | Use only that directory's `.iterm/default.yaml`, then `.yml` |

The `.` target is deliberately an automatic-discovery special case; use `./`
for explicit current-directory lookup. Explicit directories do not walk upward.

## Paths inside YAML

Resolve the definition file first. If its parent directory is named `.iterm`,
use the directory containing `.iterm/` as the base; otherwise use the YAML file's
directory. Resolve `root` (default `.`) against that base and pane `cwd` (default
`.`) against the resolved root. Expand `~` and environment variables in `root`
and `cwd`; resolve symlinks and require those directories to exist.

Thus, `root: .` in `project/.iterm/default.yaml` means `project/`, while the same
setting in `~/.iterm/default.yaml` means the home directory. In
`examples/demo.yaml`, it means `examples/`. An absolute `root` or `cwd` overrides
its relative base. These are resolution rules, not a sandbox: absolute paths and
`..` are supported. The shell must be an absolute path to an executable file.

See [the README](../README.md) for the complete YAML schema and startup-script
behavior.
