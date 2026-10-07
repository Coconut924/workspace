"""Build with the same Python environment used for project development."""

import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != "darwin":
        raise SystemExit("Standalone builds require macOS; build each architecture natively.")
    from workspace import __version__

    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    if version != __version__:
        raise SystemExit("pyproject.toml and workspace.__version__ must match before building")
    build_env = {**os.environ, "PYINSTALLER_CONFIG_DIR": str(ROOT / "build/cache")}
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            "workspace",
            "--distpath",
            str(ROOT / "dist"),
            "--workpath",
            str(ROOT / "build"),
            "--specpath",
            str(ROOT / "build"),
            "--paths",
            str(ROOT / "src"),
            "--collect-submodules",
            "websockets",
            "--copy-metadata",
            "iterm2",
            "--exclude-module",
            "pytest",
            "--exclude-module",
            "ruff",
            str(ROOT / "scripts/workspace_entry.py"),
        ],
        check=True,
        cwd=ROOT,
        env=build_env,
    )
    # Run outside the checkout with no Python environment/path overrides.
    env = {
        k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"}
    }
    env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    binary = ROOT / "dist/workspace"
    with tempfile.TemporaryDirectory() as directory:
        subprocess.run([str(binary), "--version"], cwd=directory, env=env, check=True)
        subprocess.run([str(binary), "init"], cwd=directory, env=env, check=True)
        subprocess.run([str(binary), "validate"], cwd=directory, env=env, check=True)
        subprocess.run(
            [str(binary), "--dry-run"],
            cwd=directory,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
        )
    print(f"Standalone executable verified: {binary}")


if __name__ == "__main__":
    main()
