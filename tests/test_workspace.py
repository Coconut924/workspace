import asyncio
import json
import subprocess
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from workspace.backend import build, startup_text
from workspace.cli import main
from workspace.config import ConfigError, discover, load


def config(tmp_path, text="layout: {name: shell}\n"):
    path = tmp_path / ".workspace.yaml"
    path.write_text(text)
    return load(path)


def test_paths_env_and_defaults(tmp_path):
    (tmp_path / "logs").mkdir()
    cfg = config(
        tmp_path,
        """env: {SHARED: value, OVERRIDE: base}
layout:
  name: logs
  cwd: logs
  env: {OVERRIDE: pane}
""",
    )
    assert cfg.root == tmp_path
    assert cfg.panes[0].cwd == tmp_path / "logs"
    assert cfg.panes[0].env == {"SHARED": "value", "OVERRIDE": "pane"}


@pytest.mark.parametrize(
    "text",
    [
        "layout: {name: a, typo: x}",
        "layout: {name: a, color: blue}",
        "layout: {name: a, env: {PORT: 80}}",
        "layout: {name: a, env: {BAD-NAME: x}}",
        "layout: {name: a, cwd: missing}",
        "layout: {name: a, command: 123}",
        "layout: {name: a, name: b}",
        "layout: {direction: diagonal, first: {name: a}, second: {name: b}}",
        "layout: {direction: horizontal, first: {name: a}}",
        "layout: {direction: horizontal, first: {name: a}, second: {name: a}}",
        "layout: &cycle {direction: horizontal, first: *cycle, second: {name: a}}",
        "version: true\nlayout: {name: a}",
        "shell: zsh\nlayout: {name: a}",
        "layout: []",
        "",
        "layout: [",
        "oops: x\nlayout: {name: a}",
    ],
)
def test_bad_config(tmp_path, text):
    with pytest.raises(ConfigError):
        config(tmp_path, text)


def test_discovery_respects_git_boundary_and_worktree(tmp_path):
    parent = tmp_path / ".workspace.yaml"
    parent.write_text("layout: {name: parent}")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").write_text("gitdir: elsewhere")
    nested = repo / "src"
    nested.mkdir()
    with pytest.raises(ConfigError):
        discover(None, nested)
    local = repo / ".workspace.yaml"
    local.write_text("layout: {name: local}")
    assert discover(None, nested) == local
    assert discover(".", nested) == local


def test_named_and_explicit(tmp_path):
    directory = tmp_path / "settings"
    (directory / "workspaces").mkdir(parents=True)
    preset = directory / "workspaces" / "demo.yml"
    preset.write_text("layout: {name: demo}")
    assert discover("demo", tmp_path, directory) == preset
    assert discover(str(preset), tmp_path) == preset
    with pytest.raises(ConfigError):
        discover("unknown", tmp_path, directory)


def test_shell_quoting_and_multiline(tmp_path):
    directory = tmp_path / "space ' $(touch bad)"
    directory.mkdir()
    cfg = config(
        tmp_path,
        """layout:
  name: test
  env: {VALUE: "spaces ' and $(touch bad)"}
  command: |
    printf '%s\\n' "$VALUE"
    pwd
""",
    )
    pane = cfg.panes[0]
    from dataclasses import replace

    pane = replace(pane, cwd=directory)
    result = subprocess.run(
        ["/bin/sh", "-c", startup_text(pane, "/bin/sh")], capture_output=True, text=True, check=True
    )
    assert "spaces ' and $(touch bad)" in result.stdout
    assert str(directory) in result.stdout
    assert not (tmp_path / "bad").exists()
    assert "printf" not in startup_text(pane, "/bin/sh", True)


class Custom:
    def __init__(self):
        self.values = {}

    def __getattr__(self, name):
        if name.startswith("set_"):
            return lambda value: self.values.update({name[4:]: value})
        raise AttributeError(name)


class Session:
    def __init__(self, events, name):
        self.events = events
        self.name = name
        self.async_set_name = AsyncMock()

    async def async_split_pane(self, **kwargs):
        name = kwargs["profile_customizations"].values["name"]
        self.events.append(("split", self.name, name, kwargs["vertical"]))
        return Session(self.events, name)

    async def async_send_text(self, text):
        self.events.append(("send", self.name, text))

    async def async_activate(self):
        self.events.append(("activate", self.name))


def fake_api():
    events = []
    window = SimpleNamespace(
        current_tab=SimpleNamespace(
            current_session=Session(events, "shell"), async_set_title=AsyncMock()
        ),
        async_close=AsyncMock(),
    )
    app = SimpleNamespace(async_activate=AsyncMock())
    api = SimpleNamespace(
        LocalWriteOnlyProfile=Custom,
        TitleComponents=SimpleNamespace(PROFILE_NAME=32),
        Color=lambda *rgb: rgb,
        async_get_app=AsyncMock(return_value=app),
        PartialProfile=SimpleNamespace(async_query=AsyncMock(return_value=[])),
        Window=SimpleNamespace(async_create=AsyncMock(return_value=window)),
    )
    return api, window, events


def tree_config(tmp_path):
    return config(
        tmp_path,
        """name: Test
layout:
  direction: horizontal
  first:
    direction: vertical
    first: {name: shell, color: '#182230'}
    second: {name: logs, command: 'echo logs'}
  second: {name: server, command: 'echo server'}
""",
    )


def test_layout_order_and_commands(tmp_path):
    cfg = tree_config(tmp_path)
    api, window, events = fake_api()
    asyncio.run(build(None, cfg, api))
    assert events[:2] == [("split", "shell", "server", True), ("split", "shell", "logs", False)]
    assert [event[1] for event in events if event[0] == "send"] == ["shell", "logs", "server"]
    assert [event[0] for event in events] == ["split", "split", "send", "send", "send", "activate"]
    custom = api.Window.async_create.call_args.kwargs["profile_customizations"]
    assert custom.values["background_color"] == (24, 34, 48)
    assert custom.values["use_custom_command"] == "Yes"
    window.current_tab.async_set_title.assert_awaited_once_with("Test")
    window.async_close.assert_not_awaited()


def test_split_failure_closes_only_new_window_before_commands(tmp_path):
    api, window, events = fake_api()
    window.current_tab.current_session.async_split_pane = AsyncMock(
        side_effect=RuntimeError("split")
    )
    with pytest.raises(RuntimeError, match="split"):
        asyncio.run(build(None, tree_config(tmp_path), api))
    window.async_close.assert_awaited_once_with(force=True)
    assert not events


def test_missing_profile_creates_nothing(tmp_path):
    api, _window, _events = fake_api()
    cfg = config(tmp_path, "profile: Missing\nlayout: {name: shell}")
    with pytest.raises(ConfigError, match="Unknown iTerm profiles"):
        asyncio.run(build(None, cfg, api))
    api.Window.async_create.assert_not_awaited()


def test_cli_init_validate_dry_run_list(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    original = (tmp_path / ".workspace.yaml").read_text()
    assert main(["init"]) == 1
    assert (tmp_path / ".workspace.yaml").read_text() == original
    assert main(["validate"]) == 0
    capsys.readouterr()
    assert main([".", "--dry-run"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["layout"]["second"]["name"] == "server"
    presets = tmp_path / "workspaces"
    presets.mkdir()
    (presets / "test.yaml").write_text(original)
    assert main(["list", "--config-dir", str(tmp_path)]) == 0
    assert "test\t" in capsys.readouterr().out


def test_no_commands_and_send_failure_preserves_window(tmp_path):
    cfg = tree_config(tmp_path)
    api, window, events = fake_api()
    asyncio.run(build(None, cfg, api, no_commands=True))
    assert all("echo" not in event[2] for event in events if event[0] == "send")
    api, window, events = fake_api()
    window.current_tab.current_session.async_send_text = AsyncMock(
        side_effect=RuntimeError("send failed")
    )
    with pytest.raises(RuntimeError, match="send failed"):
        asyncio.run(build(None, cfg, api))
    window.async_close.assert_not_awaited()


def test_sdk_profile_compatibility(tmp_path):
    import iterm2

    from workspace.backend import custom_profile

    cfg = tree_config(tmp_path)
    custom = custom_profile(iterm2, cfg.panes[0], cfg.shell)
    assert custom is not None


def test_four_pane_grid(tmp_path):
    cfg = config(
        tmp_path,
        """layout:
  direction: vertical
  first:
    direction: horizontal
    first: {name: shell}
    second: {name: top-right}
  second:
    direction: horizontal
    first: {name: bottom-left}
    second: {name: bottom-right}
""",
    )
    api, _window, events = fake_api()
    asyncio.run(build(None, cfg, api))
    assert events[:3] == [
        ("split", "shell", "bottom-left", False),
        ("split", "shell", "top-right", True),
        ("split", "bottom-left", "bottom-right", True),
    ]


def test_pane_limit(tmp_path):
    import yaml

    def tree(names):
        if len(names) == 1:
            return {"name": names[0]}
        mid = len(names) // 2
        return {"direction": "horizontal", "first": tree(names[:mid]), "second": tree(names[mid:])}

    with pytest.raises(ConfigError, match="At most 16"):
        config(tmp_path, yaml.safe_dump({"layout": tree([f"pane{i}" for i in range(17)])}))


@pytest.mark.parametrize("value", ["blue", "#123", "#gggggg", 42])
def test_invalid_tab_color(tmp_path, value):
    import yaml

    with pytest.raises(ConfigError, match="tab_color"):
        config(tmp_path, yaml.safe_dump({"tab_color": value, "layout": {"name": "shell"}}))


def test_tab_color_applied_to_every_pane(tmp_path):
    from workspace.backend import custom_profile

    cfg = tree_config(tmp_path)
    from dataclasses import replace

    cfg = replace(cfg, tab_color="#4779b8")
    api, _window, _events = fake_api()
    for pane in cfg.panes:
        profile = custom_profile(api, pane, cfg.shell, cfg.tab_color)
        assert profile.values["tab_color"] == (71, 121, 184)
        assert profile.values["use_tab_color"] is True
    assert "tab_color" not in custom_profile(api, cfg.panes[0], cfg.shell).values
