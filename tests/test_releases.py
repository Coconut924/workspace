"""Checks for release formula generation and version consistency."""

import importlib.util
import tomllib
from pathlib import Path

import pytest

from workspace import __version__

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publish_tap", ROOT / "scripts/publish_tap.py")
publish_tap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish_tap)


def test_version_consistency():
    assert tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"] == __version__


def test_formula_downloads_both_architectures_and_installs_binary():
    text = publish_tap.formula("1.2.3", {"arm64": "a" * 64, "x86_64": "b" * 64})
    assert "on_arm do" in text and "on_intel do" in text
    assert "v1.2.3/workspace-1.2.3-macos-arm64.tar.gz" in text
    assert "v1.2.3/workspace-1.2.3-macos-x86_64.tar.gz" in text
    assert 'bin.install "workspace"' in text
    assert 'sha256 "' + "a" * 64 + '"' in text
    assert 'depends_on "python' not in text.lower()
    assert 'system "#{bin}/workspace", "validate"' in text


@pytest.mark.parametrize("version", ["1.2", '1.2.3"; evil', "../test", "1.2.3-beta"])
def test_formula_rejects_invalid_versions(version):
    with pytest.raises(ValueError):
        publish_tap.formula(version, {"arm64": "a" * 64, "x86_64": "b" * 64})


def test_formula_rejects_invalid_checksum():
    with pytest.raises(ValueError):
        publish_tap.formula("1.2.3", {"arm64": "invalid", "x86_64": "b" * 64})
