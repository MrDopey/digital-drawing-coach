import tomllib
from pathlib import Path


def _read_version() -> str:
    pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    try:
        version = tomllib.loads(pyproject.read_text())["project"]["version"]
    except (FileNotFoundError, KeyError):
        return "dev"
    return f"{version}-prerelease"


__version__ = _read_version()
