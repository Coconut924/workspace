"""Configuration parsing and discovery, independent of iTerm2."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml


class ConfigError(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys instead of silently discarding user input."""


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str):
            raise ConfigError("YAML mapping keys must be strings")
        if key in result:
            raise ConfigError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


@dataclass(frozen=True)
class Pane:
    name: str
    cwd: Path
    profile: str | None
    color: str | None
    command: str | None
    env: dict[str, str]


@dataclass(frozen=True)
class Split:
    direction: str
    first: "Pane | Split"
    second: "Pane | Split"


@dataclass(frozen=True)
class Workspace:
    name: str
    source: Path
    root: Path
    shell: str
    tab_color: str | None
    layout: Pane | Split

    @property
    def panes(self):
        return list(leaves(self.layout))


def leaves(node):
    if isinstance(node, Pane):
        yield node
    else:
        yield from leaves(node.first)
        yield from leaves(node.second)


def config_dir():
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "workspace"


def discover(target: str | None, cwd: Path | None = None, directory: Path | None = None):
    cwd = (cwd or Path.cwd()).resolve()
    directory = directory or config_dir()
    if target is None or target == ".":
        for parent in (cwd, *cwd.parents):
            candidate = parent / ".workspace.yaml"
            if candidate.is_file():
                return candidate
            if (parent / ".git").exists():
                break
        raise ConfigError(
            "No .workspace.yaml found before the repository boundary; run workspace init"
        )
    path = Path(target).expanduser()
    if path.is_absolute() or "/" in target or path.suffix in {".yaml", ".yml"}:
        path = path if path.is_absolute() else cwd / path
        if path.is_dir():
            path /= ".workspace.yaml"
        if not path.is_file():
            raise ConfigError(f"Configuration does not exist: {path}")
        return path.resolve()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", target):
        raise ConfigError("Preset names may contain letters, digits, underscores and hyphens")
    for suffix in (".yaml", ".yml"):
        path = directory / "workspaces" / (target + suffix)
        if path.is_file():
            return path.resolve()
    raise ConfigError(
        f"Unknown preset {target!r}; expected {directory / 'workspaces' / (target + '.yaml')}"
    )


def _text(value, context):
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ConfigError(f"{context} must be a nonempty string without NUL characters")
    return value


def _keys(value, allowed, context):
    if not isinstance(value, dict):
        raise ConfigError(f"{context} must be a mapping")
    unknown = value.keys() - allowed
    if unknown:
        raise ConfigError(f"Unknown keys in {context}: {', '.join(sorted(unknown))}")


def _path(value, base, context):
    value = _text(value, context)
    path = Path(os.path.expandvars(os.path.expanduser(value)))
    path = (base / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_dir():
        raise ConfigError(f"{context} directory does not exist: {path}")
    return path


def load(path: Path):
    path = path.resolve()
    try:
        data = yaml.load(path.read_text(), Loader=UniqueLoader)
    except (OSError, yaml.YAMLError, RecursionError) as exc:
        raise ConfigError(f"Cannot read {path}: {exc}") from exc
    _keys(
        data,
        {"version", "name", "root", "shell", "profile", "env", "tab_color", "layout"},
        "workspace",
    )
    if type(data.get("version", 1)) is not int or data.get("version", 1) != 1:
        raise ConfigError("Only configuration version 1 is supported")
    name = _text(data.get("name", path.parent.name), "name")
    root = _path(data.get("root", "."), path.parent, "root")
    shell = _text(data.get("shell", "/bin/zsh"), "shell")
    if not Path(shell).is_absolute() or not os.access(shell, os.X_OK) or not Path(shell).is_file():
        raise ConfigError("shell must be an absolute path to an executable")
    profile = data.get("profile")
    if profile is not None:
        _text(profile, "profile")
    tab_color = data.get("tab_color")
    if tab_color is not None and (
        not isinstance(tab_color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", tab_color)
    ):
        raise ConfigError("tab_color must be quoted '#RRGGBB'")
    names = set()

    def environment(value):
        if not isinstance(value, dict):
            raise ConfigError("env must be a mapping of strings")
        for key, val in value.items():
            if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                raise ConfigError(f"Invalid environment variable name: {key!r}")
            if not isinstance(val, str) or "\x00" in val:
                raise ConfigError(f"env.{key} must be a string without NUL characters")
        return value

    env = environment(data.get("env", {}))

    def parse(node, depth=0):
        if depth > 8:
            raise ConfigError("Layout nesting exceeds 8 levels (or contains a YAML alias cycle)")
        if isinstance(node, dict) and "direction" in node:
            _keys(node, {"direction", "first", "second"}, "split")
            if node["direction"] not in ("horizontal", "vertical"):
                raise ConfigError(
                    "direction must be horizontal (side by side) or vertical (stacked)"
                )
            if "first" not in node or "second" not in node:
                raise ConfigError("Each split requires first and second children")
            return Split(
                node["direction"], parse(node["first"], depth + 1), parse(node["second"], depth + 1)
            )
        _keys(node, {"name", "cwd", "profile", "color", "command", "env"}, "pane")
        pane_name = _text(node.get("name"), "pane.name")
        if pane_name in names:
            raise ConfigError(f"Duplicate pane name: {pane_name}")
        names.add(pane_name)
        color = node.get("color")
        if color is not None and (
            not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color)
        ):
            raise ConfigError(f"{pane_name}: color must be quoted '#RRGGBB'")
        command = node.get("command")
        if command is not None:
            _text(command, f"{pane_name}.command")
        pane_profile = node.get("profile", profile)
        if pane_profile is not None:
            _text(pane_profile, f"{pane_name}.profile")
        return Pane(
            pane_name,
            _path(node.get("cwd", "."), root, f"{pane_name}.cwd"),
            pane_profile,
            color,
            command,
            {**env, **environment(node.get("env", {}))},
        )

    layout = parse(data.get("layout"))
    if len(names) > 16:
        raise ConfigError("At most 16 panes are supported")
    return Workspace(name, path, root, shell, tab_color, layout)
