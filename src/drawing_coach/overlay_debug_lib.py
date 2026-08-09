"""Pure coordinate-hypothesis logic for scripts/overlay_debug_tool.py."""

from __future__ import annotations

import numpy as np
from PIL import Image

_WHITE_THRESHOLD = 235
_MIN_WHITE_FRACTION = 0.5
_MIN_SPAN_RATIO = 0.15


def detect_canvas_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    """Best-effort detection of a light/white canvas rectangle within a captured
    app window, by finding the longest span of columns/rows that are mostly
    near-white. Assumes a light-background drawing surface; returns None if no
    confident band is found (e.g. a dark-themed canvas), so callers can skip
    the canvas-relative hypothesis rather than render it against a wrong box."""
    arr = np.asarray(image.convert("RGB"))
    white = np.all(arr > _WHITE_THRESHOLD, axis=2)

    x0, x1 = _longest_run(white.mean(axis=0))
    if x1 - x0 < image.width * _MIN_SPAN_RATIO:
        return None

    y0, y1 = _longest_run(white[:, x0:x1].mean(axis=1))
    if y1 - y0 < image.height * _MIN_SPAN_RATIO:
        return None

    return (int(x0), int(y0), int(x1), int(y1))


def _longest_run(fraction: np.ndarray) -> tuple[int, int]:
    best = (0, 0)
    start: int | None = None
    for i, v in enumerate(fraction):
        if v > _MIN_WHITE_FRACTION:
            if start is None:
                start = i
        elif start is not None:
            if i - start > best[1] - best[0]:
                best = (start, i)
            start = None
    if start is not None and len(fraction) - start > best[1] - best[0]:
        best = (start, len(fraction))
    return best


def _project_annotations(annotations: list[dict], pt, rad) -> list[dict]:
    shapes = []
    for ann in annotations:
        atype = ann.get("type")
        label = ann.get("label") or ""
        if atype == "arrow" and ann.get("from") and ann.get("to"):
            shapes.append(
                dict(type="arrow", p1=pt(*ann["from"]), p2=pt(*ann["to"]), label=label)
            )
        elif atype == "line" and ann.get("points"):
            shapes.append(
                dict(
                    type="line",
                    points=[pt(x, y) for x, y in ann["points"]],
                    label=label,
                )
            )
        elif (
            atype == "circle"
            and ann.get("center") is not None
            and ann.get("radius") is not None
        ):
            cx, cy = ann["center"]
            shapes.append(
                dict(
                    type="circle",
                    center=pt(cx, cy),
                    radius=rad(ann["radius"]),
                    label=label,
                )
            )
    return shapes


def compute_hypotheses(
    annotations: list[dict],
    image_w: int,
    image_h: int,
    canvas_bbox: tuple[int, int, int, int] | None = None,
    character_bbox: tuple[int, int, int, int] | None = None,
) -> list[dict]:
    """Re-projects the same annotation list under several assumptions about what
    the LLM's normalised [0,1] coordinates might actually be relative to.
    Returns a list of {key, label, color, default, desc, formula, shapes}."""
    w, h = image_w, image_h
    s = min(w, h)
    off_x, off_y = (w - s) / 2, (h - s) / 2

    defs = [
        (
            "h0",
            "H0 · Full image (as instructed)",
            "#ef4444",  # theme-exempt
            True,
            "The literal reading of the prompt: coordinates normalised to the "
            "whole captured window, chrome included. This is what "
            "overlay_renderer.py actually draws today.",
            "px = x·W, py = y·H",
            lambda x, y: (x * w, y * h),
            lambda r: r * min(w, h),
        ),
    ]

    if canvas_bbox:
        cx0, cy0, cx1, cy1 = canvas_bbox
        cw, ch = cx1 - cx0, cy1 - cy0
        defs.append(
            (
                "h1",
                "H1 · Canvas-relative",
                "#22d3ee",  # theme-exempt
                False,
                "If the model treated the detected light canvas area as the "
                "whole frame, ignoring surrounding browser/toolbar chrome.",
                "px = cx0+x·cw, py = cy0+y·ch",
                lambda x, y: (cx0 + x * cw, cy0 + y * ch),
                lambda r: r * min(cw, ch),
            )
        )

    defs.extend(
        [
            (
                "h2",
                "H2 · Square-frame assumption",
                "#4ade80",  # theme-exempt
                False,
                "If the model pictured a square capture (side = min(W,H)) "
                "centered in the frame, e.g. from training on mostly-square "
                "reference images.",
                "px = offX+x·S, py = y·S  (S=min(W,H))",
                lambda x, y: (off_x + x * s, off_y + y * s),
                lambda r: r * s,
            ),
            (
                "h3",
                "H3 · Y-axis flipped",
                "#e879f9",  # theme-exempt
                False,
                "If the model used a bottom-left origin instead of the "
                "top-left image convention.",
                "px = x·W, py = (1−y)·H",
                lambda x, y: (x * w, (1 - y) * h),
                lambda r: r * min(w, h),
            ),
            (
                "h4",
                "H4 · X/Y swapped",
                "#eab308",  # theme-exempt
                False,
                "If the model emitted (row, col) pairs instead of the "
                "requested (x, y) — a common axis-order mixup.",
                "px = y·W, py = x·H",
                lambda x, y: (y * w, x * h),
                lambda r: r * min(w, h),
            ),
        ]
    )

    if character_bbox:
        bx0, by0, bx1, by1 = character_bbox
        bw, bh = bx1 - bx0, by1 - by0
        defs.append(
            (
                "h5",
                "H5 · Character-box-relative",
                "#818cf8",  # theme-exempt
                True,
                "If the model localised the figure itself — ignoring canvas "
                "whitespace and any unrelated doodles elsewhere on the "
                "canvas — and normalised coordinates to the box you drew.",
                "px = bx0+x·bw, py = by0+y·bh",
                lambda x, y: (bx0 + x * bw, by0 + y * bh),
                lambda r: r * min(bw, bh),
            )
        )

    return [
        dict(
            key=key,
            label=label,
            color=color,
            default=default,
            desc=desc,
            formula=formula,
            shapes=_project_annotations(annotations, pt, rad),
        )
        for key, label, color, default, desc, formula, pt, rad in defs
    ]
