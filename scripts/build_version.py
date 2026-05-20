#!/usr/bin/env python3
"""Write src/drawing_coach/_version.py from GITHUB_REF_NAME env var."""
import os
from pathlib import Path

ref = os.environ.get("GITHUB_REF_NAME", "")
version = ref.lstrip("v") if ref else "dev"

out = Path(__file__).parent.parent / "src" / "drawing_coach" / "_version.py"
out.write_text(f'__version__ = "{version}"\n')
print(f"Version set to: {version}")
