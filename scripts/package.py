"""Build a native release archive and its checksum."""

import hashlib
import platform
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    subprocess.run([sys.executable, str(ROOT / "scripts/build.py")], check=True)
    arch = platform.machine()
    if arch not in {"arm64", "x86_64"}:
        raise SystemExit(f"Unsupported architecture: {arch}")
    archive = ROOT / "dist" / f"workspace-{version}-macos-{arch}.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(ROOT / "dist/workspace", arcname="workspace")
        bundle.add(ROOT / "README.md", arcname="README.md")
        bundle.add(ROOT / "examples", arcname="examples")
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(archive.suffix + ".sha256").write_text(f"{checksum}  {archive.name}\n")
    print(f"Packaged {archive.name}\nSHA-256: {checksum}")


if __name__ == "__main__":
    main()
