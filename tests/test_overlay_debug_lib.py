from PIL import Image, ImageDraw

from drawing_coach.overlay_debug_lib import compute_hypotheses, detect_canvas_bbox


def _image_with_canvas() -> Image.Image:
    img = Image.new("RGB", (400, 300), color=(20, 20, 25))
    ImageDraw.Draw(img).rectangle([100, 50, 300, 250], fill=(255, 255, 255))
    return img


def test_detect_canvas_bbox_finds_light_rectangle():
    bbox = detect_canvas_bbox(_image_with_canvas())
    x0, y0, x1, y1 = bbox
    assert abs(x0 - 100) <= 2
    assert abs(y0 - 50) <= 2
    assert abs(x1 - 300) <= 2
    assert abs(y1 - 250) <= 2


def test_detect_canvas_bbox_returns_none_without_a_light_region():
    img = Image.new("RGB", (400, 300), color=(20, 20, 25))
    assert detect_canvas_bbox(img) is None


def _sample_annotations():
    return [
        {
            "type": "arrow",
            "from": [0.5, 0.5],
            "to": [1.0, 1.0],
            "label": "eyes",
        },
        {
            "type": "line",
            "points": [[0.0, 0.0], [0.5, 0.5]],
            "label": "jaw",
        },
        {
            "type": "circle",
            "center": [0.5, 0.5],
            "radius": 0.1,
            "label": "head",
        },
    ]


def test_h0_full_image_projects_directly_by_width_and_height():
    hyps = compute_hypotheses(_sample_annotations(), image_w=1000, image_h=500)
    h0 = next(h for h in hyps if h["key"] == "h0")
    arrow = next(s for s in h0["shapes"] if s["type"] == "arrow")
    assert arrow["p1"] == (500.0, 250.0)
    assert arrow["p2"] == (1000.0, 500.0)
    circle = next(s for s in h0["shapes"] if s["type"] == "circle")
    assert circle["center"] == (500.0, 250.0)
    assert circle["radius"] == 0.1 * 500


def test_h1_canvas_relative_offsets_into_the_detected_box():
    hyps = compute_hypotheses(
        _sample_annotations(),
        image_w=1000,
        image_h=500,
        canvas_bbox=(200, 100, 800, 400),
    )
    h1 = next(h for h in hyps if h["key"] == "h1")
    circle = next(s for s in h1["shapes"] if s["type"] == "circle")
    assert circle["center"] == (200 + 0.5 * 600, 100 + 0.5 * 300)


def test_h5_only_present_when_character_bbox_given():
    without = compute_hypotheses(_sample_annotations(), image_w=1000, image_h=500)
    assert not any(h["key"] == "h5" for h in without)

    with_box = compute_hypotheses(
        _sample_annotations(),
        image_w=1000,
        image_h=500,
        character_bbox=(400, 200, 600, 300),
    )
    h5 = next(h for h in with_box if h["key"] == "h5")
    circle = next(s for s in h5["shapes"] if s["type"] == "circle")
    assert circle["center"] == (400 + 0.5 * 200, 200 + 0.5 * 100)


def test_h0_and_h5_are_checked_by_default_when_a_character_box_is_drawn():
    hyps = compute_hypotheses(
        _sample_annotations(),
        image_w=1000,
        image_h=500,
        canvas_bbox=(200, 100, 800, 400),
        character_bbox=(400, 200, 600, 300),
    )
    defaults = {h["key"]: h["default"] for h in hyps}
    assert defaults == {
        "h0": True,
        "h1": False,
        "h2": False,
        "h3": False,
        "h4": False,
        "h5": True,
    }


def test_only_h0_is_checked_by_default_without_a_character_box():
    hyps = compute_hypotheses(
        _sample_annotations(),
        image_w=1000,
        image_h=500,
        canvas_bbox=(200, 100, 800, 400),
    )
    defaults = {h["key"]: h["default"] for h in hyps}
    assert defaults == {"h0": True, "h1": False, "h2": False, "h3": False, "h4": False}
