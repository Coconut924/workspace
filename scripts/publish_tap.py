"""Generate the tap formula from verified, published release assets and push it."""

import argparse
import hashlib
import re
import subprocess
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "Coconut924/workspace"
TAP = "Coconut924/homebrew-tap"


def formula(version, checksums):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Only stable MAJOR.MINOR.PATCH versions are supported")
    for arch in ("arm64", "x86_64"):
        if not re.fullmatch(r"[0-9a-f]{64}", checksums[arch]):
            raise ValueError(f"Invalid {arch} checksum")
    return f'''class Workspace < Formula
  desc "Declarative native iTerm2 workspaces"
  homepage "https://github.com/{SOURCE}"
  version "{version}"

  depends_on :macos

  on_arm do
    url "https://github.com/{SOURCE}/releases/download/v{version}/workspace-{version}-macos-arm64.tar.gz"
    sha256 "{checksums["arm64"]}"
  end

  on_intel do
    url "https://github.com/{SOURCE}/releases/download/v{version}/workspace-{version}-macos-x86_64.tar.gz"
    sha256 "{checksums["x86_64"]}"
  end

  def install
    bin.install "workspace"
    pkgshare.install "examples"
  end

  def caveats
    <<~EOS
      Requires iTerm2 with Settings > General > Magic > Enable Python API enabled.
      Approve the workspace connection prompt on first launch.
      Examples: #{{pkgshare}}/examples
    EOS
  end

  test do
    assert_equal version.to_s, shell_output("#{{bin}}/workspace --version").strip
    system "#{{bin}}/workspace", "init"
    system "#{{bin}}/workspace", "validate"
  end
end
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        default=tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"],
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="verify downloads and print formula without pushing"
    )
    args = parser.parse_args()
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        parser.error("version must be MAJOR.MINOR.PATCH")
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        # Both architectures must already be published; no placeholders or guessed checksums.
        subprocess.run(
            [
                "gh",
                "release",
                "download",
                f"v{args.version}",
                "--repo",
                SOURCE,
                "--pattern",
                "*.tar.gz",
                "--pattern",
                "SHA256SUMS",
                "--dir",
                directory,
            ],
            check=True,
        )
        recorded = {}
        for line in (folder / "SHA256SUMS").read_text().splitlines():
            digest, name = line.split()
            if name in recorded:
                raise ValueError(f"Duplicate checksum entry: {name}")
            recorded[name] = digest
        checksums = {}
        for arch in ("arm64", "x86_64"):
            name = f"workspace-{args.version}-macos-{arch}.tar.gz"
            digest = hashlib.sha256((folder / name).read_bytes()).hexdigest()
            if digest != recorded.get(name):
                raise ValueError(f"Release checksum mismatch: {name}")
            checksums[arch] = digest
        content = formula(args.version, checksums)
        if args.dry_run:
            print(content)
            return
        checkout = folder / "tap"
        subprocess.run(["gh", "repo", "clone", TAP, str(checkout)], check=True)
        path = checkout / "Formula/workspace.rb"
        path.parent.mkdir(exist_ok=True)
        if path.exists() and path.read_text() == content:
            print(f"Tap already points to {args.version}")
            return
        path.write_text(content)
        subprocess.run(["git", "add", "Formula/workspace.rb"], cwd=checkout, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"workspace {args.version}"], cwd=checkout, check=True
        )
        subprocess.run(["git", "push", "origin", "HEAD"], cwd=checkout, check=True)
        print(f"Published {TAP}: workspace {args.version}")


if __name__ == "__main__":
    main()
