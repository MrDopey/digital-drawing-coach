"""Renders LLM annotation JSON onto a Pillow image copy."""
from __future__ import annotations

import json
import math
from typing import Any

from PIL import Image, ImageDraw, ImageFont

_COLOR_MAP = {
    "red": (220, 50, 50),
    "blue": (50, 130, 220),
    "green": (50, 200, 80),
    "yellow": (240, 200, 30),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}
_DEFAULT_COLOR = (220, 50, 50)
_LINE_WIDTH = 3
_ARROW_HEAD = 12   # pixels


def render(image: Image.Image, annotation_json: str) -> tuple[Image.Image, str | None]:
    """
    Returns (annotated_image, error_message).
    error_message is None on success, set to a fallback notice on parse failure.
    """
    try:
        data = json.loads(annotation_json)
        annotations: list[dict] = data.get("annotations", [])
    except (json.JSONDecodeError, AttributeError):
        return image, "Visual overlay unavailable — showing text feedback instead"

    out = image.copy().convert("RGBA")
    draw = ImageDraw.Draw(out)
    w, h = out.size

    for ann in annotations:
        try:
            _render_annotation(draw, ann, w, h)
        except Exception:
            continue

    return out.convert("RGB"), None


def _render_annotation(draw: ImageDraw.ImageDraw, ann: dict, w: int, h: int) -> None:
    atype = ann.get("type", "")
    color = _resolve_color(ann.get("color", "red"))

    if atype == "arrow":
        fx, fy = ann["from"]
        tx, ty = ann["to"]
        p1 = (int(fx * w), int(fy * h))
        p2 = (int(tx * w), int(ty * h))
        draw.line([p1, p2], fill=color, width=_LINE_WIDTH)
        _draw_arrowhead(draw, p1, p2, color)
        label = ann.get("label", "")
        if label:
            draw.text((p2[0] + 6, p2[1] - 10), label, fill=color)

    elif atype == "line":
        points = [(int(px * w), int(py * h)) for px, py in ann["points"]]
        if len(points) >= 2:
            draw.line(points, fill=color, width=_LINE_WIDTH)

    elif atype == "circle":
        cx, cy = ann["center"]
        r = ann["radius"]
        px, py = int(cx * w), int(cy * h)
        pr = int(r * min(w, h))
        bbox = [px - pr, py - pr, px + pr, py + pr]
        draw.ellipse(bbox, outline=color, width=_LINE_WIDTH)
        label = ann.get("label", "")
        if label:
            draw.text((px - pr, py - pr - 16), label, fill=color)


def _draw_arrowhead(
    draw: ImageDraw.ImageDraw,
    p1: tuple[int, int],
    p2: tuple[int, int],
    color: tuple[int, int, int],
) -> None:
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    # Two wing points of the arrowhead
    ax = p2[0] - _ARROW_HEAD * ux + (_ARROW_HEAD / 2) * (-uy)
    ay = p2[1] - _ARROW_HEAD * uy + (_ARROW_HEAD / 2) * ux
    bx = p2[0] - _ARROW_HEAD * ux - (_ARROW_HEAD / 2) * (-uy)
    by = p2[1] - _ARROW_HEAD * uy - (_ARROW_HEAD / 2) * ux
    draw.polygon(
        [p2, (int(ax), int(ay)), (int(bx), int(by))],
        fill=color,
    )


def _resolve_color(name: str | list) -> tuple[int, int, int]:
    if isinstance(name, (list, tuple)) and len(name) >= 3:
        return tuple(int(c) for c in name[:3])  # type: ignore[return-value]
    return _COLOR_MAP.get(str(name).lower(), _DEFAULT_COLOR)
