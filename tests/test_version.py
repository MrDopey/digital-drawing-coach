import importlib.util
from pathlib import Path

from drawing_coach._version import __version__

VERSION_SRC = (
    Path(__file__).parent.parent / "src" / "drawing_coach" / "_version.py"
).read_text()


def _load_version_module(repo_root: Path):
    module_dir = repo_root / "src" / "drawing_coach"
    module_dir.mkdir(parents=True, exist_ok=True)
    module_path = module_dir / "_version.py"
    module_path.write_text(VERSION_SRC)

    spec = importlib.util.spec_from_file_location("_version_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_version_is_non_empty_string():
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_reads_pyproject_and_appends_prerelease_suffix(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\nversion = "1.4.2"\n'
    )
    module = _load_version_module(tmp_path)
    assert module.__version__ == "1.4.2-prerelease"


def test_falls_back_to_dev_when_pyproject_is_missing(tmp_path):
    module = _load_version_module(tmp_path)
    assert module.__version__ == "dev"
