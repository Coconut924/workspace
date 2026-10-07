# iTerm Workspace

Create a native iTerm2 window from a YAML definition:

```sh
workspace relay
workspace .
workspace ./examples/demo.yaml
```

Each pane has its own name, background color, working directory, optional iTerm
profile, environment variables, and startup script. No tmux is required.
Each launch creates a new window. Existing windows and saved profiles are untouched.

## Install

For the standalone release (no Python or repository checkout required):

```sh
brew tap Coconut924/tap
brew install Coconut924/tap/workspace
```

Enable iTerm2's Python API as described below. To build an executable yourself,
run `mise run build`; to create a release archive, run `mise run package`.
See [Packaging and Homebrew releases](docs/releases.md) for the full build,
versioning, GitHub Release, and tap update process.

### Development installation

Requires macOS, iTerm2, and Python 3.11+. This project uses mise for Python.
From this repository:

```sh
mise install
mise run setup
source .venv/bin/activate
workspace --help
```

The `workspace` executable lives in `.venv/bin`. Activate the environment before
using it, or invoke `/absolute/path/to/workspace/.venv/bin/workspace` from a shell
script or launcher. No global dependencies are installed. With an existing Python
3.11+ you can instead run `python3 -m venv .venv`, then
`.venv/bin/python -m pip install -e '.[dev]'`.

In iTerm2, enable **Settings → General → Magic → Enable Python API**. Approve
its authorization prompt the first time this CLI connects. iTerm is launched
automatically. If connection is pending, check iTerm for a prompt; Ctrl-C cancels.

Try the demo (it only prints readiness messages):

```sh
workspace validate examples/demo.yaml
workspace examples/demo.yaml --dry-run
workspace examples/demo.yaml
```

## Project and home definitions

```sh
cd ~/Projects/my-project
workspace init              # creates .iterm/default.yaml without overwriting
# Edit .iterm/default.yaml
workspace .                 # launches this project's workspace
workspace                   # same automatic discovery
workspace validate          # checks it without opening iTerm
workspace --no-commands     # colors, directories and env, without startup scripts
```

Definitions live in hidden `.iterm/` directories:

```text
my-project/
  .iterm/
    default.yaml
    dev.yaml
    debug.yaml
```

Discovery walks upward from the current directory to the nearest `.iterm/`, stopping
at the first Git repository root (including worktrees). It looks for the requested
name there, then falls back to `~/.iterm/`. It does not search additional parent
`.iterm/` directories. With no name, the requested definition is `default`.
Both `.yaml` and `.yml` are supported; `.yaml` takes precedence within each directory.

```sh
workspace                   # discover default.yaml (or default.yml)
workspace .                 # same automatic discovery
workspace dev               # discover .iterm/dev.yaml, then ~/.iterm/dev.yaml
workspace file.yaml         # explicit file in the current directory
workspace ./path/file.yaml  # explicit file path
workspace ./project/        # only ./project/.iterm/default.yaml (or default.yml)
```

Explicit paths do not fall back to home definitions. Add `.iterm/` to your project's
`.gitignore` to keep local definitions out of Git, or commit them to share layouts.

Home definitions are available across projects:

```sh
mkdir -p ~/.iterm
cp examples/relay.yaml ~/.iterm/relay.yaml
# Change root and commands to match your project
workspace list
workspace validate relay
workspace relay
```

`workspace list` shows available project and home definitions, with project names
overriding home names. Use `--config-dir /path/to/definitions` to replace the home
fallback directory. Names use letters, digits, underscores and hyphens. `init`,
`list`, and `validate` are reserved CLI commands; use an explicit path for definitions
with those names. `workspace validate dev` validates a named definition.

## Configuration

```yaml
version: 1
name: My project
tab_color: "#4779b8"         # optional tab color, independent of pane backgrounds
root: .
shell: /bin/zsh
# profile: Default            # optional existing iTerm profile, inherited by panes
env:
  APP_ENV: development
layout:
  direction: horizontal     # side by side: first left, second right
  first:
    direction: vertical     # stacked: first above, second below
    first:
      name: shell
      color: "#182230"
    second:
      name: logs
      color: "#291c20"
      cwd: logs             # relative to root; must already exist
      command: tail -f app.log
  second:
    name: server
    color: "#17251d"
    env:
      PORT: "8080"
    command: |
      echo "Starting on $PORT"
      ./start-server.sh
```

A layout is either a pane or a split with exactly `direction`, `first`, and
`second`. Nest splits to create grids or asymmetric arrangements. Splits divide
the available pane approximately in half; ratios are not configurable. The
orientation describes placement, not the iTerm divider's orientation.

Workspace fields:

| Field | Default | Meaning |
| --- | --- | --- |
| `version` | `1` | Schema version; only 1 is supported |
| `name` | Base directory name | Tab title |
| `root` | `.` | Relative to the directory containing `.iterm/`, or the YAML's directory for other files |
| `tab_color` | Profile tab color | Quoted `#RRGGBB`, applied to all panes so focus changes preserve it |
| `shell` | `/bin/zsh` | Absolute executable shell path; requires POSIX shell syntax and `-l -c` support |
| `profile` | iTerm default | Existing iTerm profile inherited by panes |
| `env` | `{}` | Environment shared by panes |
| `layout` | Required | Pane or nested split |

Pane fields:

| Field | Default | Meaning |
| --- | --- | --- |
| `name` | Required | Unique session name |
| `cwd` | `.` | Directory relative to workspace root |
| `profile` | Workspace profile | Existing iTerm profile override |
| `color` | Profile background | Quoted `#RRGGBB` session background |
| `env` | `{}` | Overrides shared env; values must be strings |
| `command` | None | Shell script to run once after layout creation |

Paths expand `~` and environment variables. Directories must exist; validation
rejects unknown fields, duplicate YAML keys, duplicate pane names, invalid colors,
invalid env names, cycles/deep layouts, and more than 16 panes. Configuration
validation is offline; iTerm profile names are checked on connection before
window creation. Shells start as login shells; your login configuration supplies
PATH and tools such as mise.

For `.iterm/default.yaml`, `root: .` means the project directory. For
`~/.iterm/relay.yaml`, it means your home directory; set `root: ~/Projects/relay`
to launch in that project. Explicit YAML files outside `.iterm/` resolve relative
paths from the YAML file's directory.

Startup scripts run in a child login shell after `cd` and environment setup. The
pane remains interactive after they exit. Changes made inside a startup script
(such as `cd`, shell functions or exports) do not persist in the interactive pane;
use `cwd` and `env` for persistent setup. Scripts are passed as one quoted shell
argument, supporting multiline scripts and paths with spaces. A command exit
status is not treated as CLI failure: the CLI sets up sessions, it does not monitor
services. `--no-commands` still applies directories and environment variables.

All layout creation completes before startup input is sent. On a split/title
failure the new window is closed before any scripts run. If sending input fails,
the partially started window remains available for inspection. The tool does not
reuse sessions, persist processes, or automatically alter every new iTerm window.
Colors are session-local and disable separate light/dark colors in those sessions.
Omit `tab_color` (or set it to `null`) to inherit tab colors from the selected profiles.
Configured tab colors also enable iTerm’s Use Tab Color setting for those sessions.

Only launch YAML you trust: `command` executes shell code. `--dry-run` does not
open iTerm or run commands, but prints the resolved environment and scripts, so
avoid sharing its output if your configuration contains secrets.

## Development

See the [development setup and verification guide](docs/development.md),
[repository conventions](docs/conventions.md), and
[definition discovery rules](docs/discovery.md). Agents should start with
[AGENTS.md](AGENTS.md). Publishing is covered in [the release guide](docs/releases.md).

```sh
mise run test
mise run lint
```

`config.py` owns discovery and strict schema validation. `backend.py` maps the
binary tree to iTerm native splits and session-local profile settings. `cli.py`
handles initialization, preset listing, validation and launch plans. Tests cover
configuration errors, discovery boundaries, quoting, and the iTerm adapter with
fake sessions. Run `.venv/bin/python tests/live_smoke.py` for a live integration check. It creates
a harmless demo, verifies geometry, pane labels, colors, directories and printed
output through the API, then closes only the window it created. Live testing
requires API access to a running iTerm instance.

API references: [iTerm2 session splitting](https://iterm2.com/python-api/session.html),
[session-local profiles](https://iterm2.com/python-api/profile.html), and
[external scripts](https://iterm2.com/python-api/examples/launch_and_run.html).
