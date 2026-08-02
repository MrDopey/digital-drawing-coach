#!/usr/bin/env python3
"""Write src/drawing_coach/_version.py from pyproject.toml's [project].version."""
import tomllib
from pathlib import Path

repo_root = Path(__file__).parent.parent
pyproject = repo_root / "pyproject.toml"
version = tomllib.loads(pyproject.read_text())["project"]["version"]

out = repo_root / "src" / "drawing_coach" / "_version.py"
out.write_text(f'__version__ = "{version}"\n')
print(f"Version set to: {version}")
