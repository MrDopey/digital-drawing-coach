import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "bump_version.py"

spec = importlib.util.spec_from_file_location("bump_version", SCRIPT_PATH)
bump_version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bump_version)


@pytest.mark.parametrize(
    "current,kind,expected",
    [
        ("1.2.3", "patch", "1.2.4"),
        ("1.2.3", "minor", "1.3.0"),
        ("1.2.3", "major", "2.0.0"),
        ("1.2.9", "patch", "1.2.10"),
        ("0.1.0", "major", "1.0.0"),
    ],
)
def test_bump_arithmetic(current, kind, expected):
    assert bump_version.bump(current, kind) == expected


def test_bump_rejects_non_semver():
    with pytest.raises(ValueError):
        bump_version.bump("not-a-version", "patch")


def test_cli_rewrites_pyproject(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "example"\nversion = "1.2.3"\ndescription = "x"\n'
    )
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script_copy = scripts_dir / "bump_version.py"
    script_copy.write_text(SCRIPT_PATH.read_text())

    result = subprocess.run(
        [sys.executable, str(script_copy), "minor"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "1.3.0"
    assert 'version = "1.3.0"' in pyproject.read_text()


def test_cli_fails_fast_on_non_semver(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "example"\nversion = "not-semver"\n')
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script_copy = scripts_dir / "bump_version.py"
    script_copy.write_text(SCRIPT_PATH.read_text())

    result = subprocess.run(
        [sys.executable, str(script_copy), "patch"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "not valid semver" in result.stderr
