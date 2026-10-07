"""Manual iTerm integration check: .venv/bin/python tests/live_smoke.py."""

from pathlib import Path

import iterm2

from workspace.backend import build
from workspace.config import load


async def main(connection):
    config = load(Path(__file__).resolve().parents[1] / "examples/demo.yaml")
    window = await build(connection, config, iterm2)
    try:
        app = await iterm2.async_get_app(connection)
        tab = app.get_window_by_id(window.window_id).current_tab
        assert len(tab.sessions) == 3
        sessions = {}
        for session in tab.sessions:
            profile = await session.async_get_profile()
            sessions[profile.name] = session
            pane = next(p for p in config.panes if p.name == profile.name)
            color = profile.background_color
            expected = tuple(int(pane.color[i : i + 2], 16) for i in (1, 3, 5))
            assert (color.red, color.green, color.blue) == expected
            # iTerm may add newer title flags unknown to the Python SDK enum.
            assert (
                profile.all_properties["Title Components"]
                & iterm2.TitleComponents.PROFILE_NAME.value
            )
            assert profile.use_tab_color
            tab_rgb = tuple(int(config.tab_color[i : i + 2], 16) for i in (1, 3, 5))
            actual = profile.tab_color
            assert (actual.red, actual.green, actual.blue) == tab_rgb
            # Poll output rather than assuming a fixed shell initialization time.
            import asyncio

            for _ in range(50):
                await app.async_refresh()
                cwd = await session.async_get_variable("path")
                content = await session.async_get_screen_contents()
                text = "\n".join(content.line(i).string for i in range(content.number_of_lines))
                ready = pane.command is None or f"{pane.name.title()} pane ready" in text
                if cwd == str(pane.cwd) and ready:
                    break
                await asyncio.sleep(0.1)
            else:
                raise AssertionError(f"{pane.name}: expected directory/output did not appear")
        shell, logs, server = (sessions[name].frame for name in ("shell", "logs", "server"))
        assert shell.origin.x == logs.origin.x
        assert shell.origin.y < logs.origin.y
        assert server.origin.x > shell.origin.x
        assert server.size.height > shell.size.height
        print("Live smoke passed: layout, names, pane/tab colors, directories and startup output")
    finally:
        await window.async_close(force=True)


iterm2.run_until_complete(main)
