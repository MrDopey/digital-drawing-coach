import json

from PIL import Image, ImageDraw

from drawing_coach.overlay_renderer import (
    _COLOR_MAP,
    _LABEL_BG_COLOR,
    _LABEL_PADDING,
    _LABEL_TEXT_COLOR,
    render,
)


_LABEL_TEXT = "Test label"
_CANVAS_COLOR = (100, 150, 200)  # distinct from both fixed label colors


def _blank_image() -> Image.Image:
    return Image.new("RGB", (200, 200), color=_CANVAS_COLOR)


def _arrow_annotation(color: str) -> str:
    return json.dumps(
        {
            "annotations": [
                {
                    "type": "arrow",
                    "from": [0.1, 0.1],
                    "to": [0.5, 0.5],
                    "label": _LABEL_TEXT,
                    "color": color,
                }
            ]
        }
    )


def _rgb(pixel) -> tuple[int, int, int]:
    return tuple(pixel[:3])


def _close(a: tuple[int, int, int], b: tuple[int, int, int], tolerance: int = 40) -> bool:
    return sum(abs(x - y) for x, y in zip(a, b)) <= tolerance


def test_label_uses_fixed_color_pair_regardless_of_annotation_color():
    base = _blank_image()
    for color_name in _COLOR_MAP:
        img, err = render(base, _arrow_annotation(color_name))
        assert err is None

        pixels = img.load()
        found_bg_color = False
        found_dark_text_pixel = False
        for x in range(img.width):
            for y in range(img.height):
                px = _rgb(pixels[x, y])
                if px == _LABEL_BG_COLOR:
                    found_bg_color = True
                if _close(px, _LABEL_TEXT_COLOR, tolerance=60):
                    found_dark_text_pixel = True

        assert found_bg_color, f"expected fixed label background for {color_name}"
        assert found_dark_text_pixel, f"expected fixed label text color for {color_name}"


def test_label_background_sized_to_text_bbox():
    base = _blank_image()
    draw = ImageDraw.Draw(base)
    pos = (20, 20)
    bbox = draw.textbbox(pos, _LABEL_TEXT)
    expected_width = (bbox[2] - bbox[0]) + 2 * _LABEL_PADDING
    expected_height = (bbox[3] - bbox[1]) + 2 * _LABEL_PADDING

    img, err = render(base, _arrow_annotation("red"))
    assert err is None

    pixels = img.load()
    bg_xs = []
    bg_ys = []
    for x in range(img.width):
        for y in range(img.height):
            if _rgb(pixels[x, y]) == _LABEL_BG_COLOR:
                bg_xs.append(x)
                bg_ys.append(y)

    assert bg_xs and bg_ys
    rendered_width = max(bg_xs) - min(bg_xs) + 1
    rendered_height = max(bg_ys) - min(bg_ys) + 1

    # Allow a small tolerance for rounding at the rectangle edges.
    assert abs(rendered_width - expected_width) <= 2
    assert abs(rendered_height - expected_height) <= 2
