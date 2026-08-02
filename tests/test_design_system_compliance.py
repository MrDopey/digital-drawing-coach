"""Guards against new inline hex colors / raw setStyleSheet() calls creeping
back into src/drawing_coach/ outside theme.py and design_system.py.

A line that must reference a color/setStyleSheet() call for a legitimate
reason (a value that varies at runtime and can't be a static token, or a
color that isn't a UI theme value at all — e.g. a decorative icon-drawing
color) is marked with a trailing `# theme-exempt` comment.
"""

from __future__ import annotations

import re
from pathlib import Path

SRC_DIR = Path(__file__).parent.parent / "src" / "drawing_coach"
EXEMPT_FILES = {"theme.py", "design_system.py"}
HEX_LITERAL = re.compile(r"#[0-9a-fA-F]{3,6}")
STYLESHEET_CALL = re.compile(r"\.setStyleSheet\(")
ESCAPE_MARKER = "# theme-exempt"


def _scan_file(path: Path) -> list[str]:
    violations = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        if ESCAPE_MARKER in line:
            continue
        if HEX_LITERAL.search(line):
            violations.append(f"{path.name}:{lineno}: hex color literal: {line.strip()}")
        if STYLESHEET_CALL.search(line):
            violations.append(f"{path.name}:{lineno}: raw setStyleSheet() call: {line.strip()}")
    return violations


def test_no_stray_hex_literals_or_setstylesheet_calls_outside_theme():
    offenders: list[str] = []
    for path in sorted(SRC_DIR.glob("*.py")):
        if path.name in EXEMPT_FILES:
            continue
        offenders.extend(_scan_file(path))

    assert not offenders, (
        "Found hardcoded hex colors or raw setStyleSheet() calls outside "
        "theme.py/design_system.py. Use a Theme token or a design_system "
        "component instead, or mark a genuinely necessary exception with "
        f"a trailing `{ESCAPE_MARKER}` comment:\n" + "\n".join(offenders)
    )


def test_escape_hatch_is_honored(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text('label.setStyleSheet("color: #123456;")  # theme-exempt\n')
    assert _scan_file(sample) == []


def test_escape_hatch_does_not_mask_unmarked_violations(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text('label.setStyleSheet("color: #123456;")\n')
    violations = _scan_file(sample)
    assert len(violations) == 2  # one hex literal, one raw setStyleSheet() call
