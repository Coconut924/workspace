"""iTerm2 adapter. Commands are sent only after the complete layout exists."""

import shlex

from .config import ConfigError, Pane, leaves


def startup_text(pane, shell, no_commands=False):
    parts = [f"cd -- {shlex.quote(str(pane.cwd))}"]
    if pane.env:
        parts.append("export " + " ".join(f"{k}={shlex.quote(v)}" for k, v in pane.env.items()))
    if pane.command and not no_commands:
        # Quote the entire script as one argument: multiline scripts do not become
        # separate interactive input lines, and the pane shell remains after exit.
        parts.append(f"{shlex.quote(shell)} -l -c {shlex.quote(pane.command)}")
    return " && ".join(parts) + "\n"


def custom_profile(api, pane, shell, tab_color=None):
    custom = api.LocalWriteOnlyProfile()
    custom.set_name(pane.name)
    custom.set_title_components([api.TitleComponents.PROFILE_NAME])
    custom.set_use_custom_command("Yes")
    custom.set_command(f"{shlex.quote(shell)} -l")
    if tab_color:
        custom.set_use_separate_colors_for_light_and_dark_mode(False)
        custom.set_use_tab_color(True)
        custom.set_tab_color(api.Color(*(int(tab_color[i : i + 2], 16) for i in (1, 3, 5))))
    if pane.color:
        rgb = [int(pane.color[i : i + 2], 16) for i in (1, 3, 5)]
        custom.set_use_separate_colors_for_light_and_dark_mode(False)
        custom.set_background_color(api.Color(*rgb))
    return custom


async def build(connection, config, api, no_commands=False, new_window=False):
    app = await api.async_get_app(connection)
    profiles = await api.PartialProfile.async_query(connection)
    available = {profile.name for profile in profiles}
    missing = {
        pane.profile for pane in config.panes if pane.profile and pane.profile not in available
    }
    if missing:
        raise ConfigError("Unknown iTerm profiles: " + ", ".join(sorted(missing)))
    first = next(leaves(config.layout))
    window = None if new_window else app.current_window
    owns_window = window is None
    customizations = custom_profile(api, first, config.shell, config.tab_color)
    if owns_window:
        window = await api.Window.async_create(
            connection, profile=first.profile, profile_customizations=customizations
        )
        tab = window.current_tab if window is not None else None
    else:
        tab = await window.async_create_tab(
            profile=first.profile, profile_customizations=customizations
        )
    created = window if owns_window else tab
    sessions = []

    async def expand(node, session):
        if isinstance(node, Pane):
            await session.async_set_name(node.name)
            sessions.append((node, session))
            return
        new_pane = next(leaves(node.second))
        new_session = await session.async_split_pane(
            vertical=node.direction == "horizontal",
            profile=new_pane.profile,
            profile_customizations=custom_profile(api, new_pane, config.shell, config.tab_color),
        )
        await expand(node.first, session)
        await expand(node.second, new_session)

    try:
        if tab is None or tab.current_session is None:
            raise RuntimeError("iTerm did not create a usable workspace tab")
        await expand(config.layout, tab.current_session)
        await tab.async_set_title(config.name)
    except Exception:
        # Close only the tab/window owned by this launch, before startup input.
        if created is not None:
            await created.async_close(force=True)
        raise
    for pane, session in sessions:
        await session.async_send_text(startup_text(pane, config.shell, no_commands))
    await sessions[0][1].async_activate()
    await app.async_activate()
    return window


def launch(config, no_commands=False, new_window=False):
    import subprocess
    import sys

    if sys.platform != "darwin":
        raise ConfigError("Launching workspaces requires macOS and iTerm2")
    import iterm2

    subprocess.run(["/usr/bin/open", "-a", "iTerm"], check=True)

    errors = []

    async def run(connection):
        # The SDK exits the interpreter when its callback raises. Capture the
        # error here so the CLI can report it without a third-party traceback.
        try:
            await build(connection, config, iterm2, no_commands, new_window=new_window)
        except Exception as exc:  # noqa: BLE001 -- SDK callback error boundary
            errors.append(exc)

    # iTerm prompts for API authorization on the first connection.
    iterm2.run_until_complete(run, retry=True)
    if errors:
        raise errors[0]
