"""Tests for MacOSBackend.capture_image (window-ID-scoped CoreGraphics capture)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from PIL import Image


def _mock_quartz(
    *,
    image_ref: object = "fake-cgimage",
    width: int = 2,
    height: int = 2,
    bytes_per_row: int | None = None,
    bits_per_pixel: int = 32,
    raw_data: bytes | None = None,
) -> MagicMock:
    bytes_per_pixel = bits_per_pixel // 8
    if bytes_per_row is None:
        bytes_per_row = width * bytes_per_pixel
    if raw_data is None:
        raw_data = bytes((i % 256) for i in range(height * bytes_per_row))

    mock_quartz = MagicMock()
    mock_quartz.CGRectNull = "CGRectNull"
    mock_quartz.kCGWindowListOptionIncludingWindow = 8
    mock_quartz.kCGWindowImageBoundsIgnoreFraming = 1
    mock_quartz.kCGWindowImageShouldBeOpaque = 2
    mock_quartz.kCGWindowImageNominalResolution = 16
    mock_quartz.CGWindowListCreateImage.return_value = image_ref
    mock_quartz.CGImageGetWidth.return_value = width
    mock_quartz.CGImageGetHeight.return_value = height
    mock_quartz.CGImageGetDataProvider.return_value = "fake-provider"
    mock_quartz.CGDataProviderCopyData.return_value = raw_data
    mock_quartz.CGImageGetBytesPerRow.return_value = bytes_per_row
    mock_quartz.CGImageGetBitsPerPixel.return_value = bits_per_pixel
    return mock_quartz


def test_capture_image_calls_createimage_with_window_id_not_rect():
    mock_quartz = _mock_quartz()
    with patch.dict("sys.modules", {"Quartz": mock_quartz}):
        from drawing_coach._backend_macos import MacOSBackend

        MacOSBackend().capture_image(42)

    mock_quartz.CGWindowListCreateImage.assert_called_once()
    args = mock_quartz.CGWindowListCreateImage.call_args[0]
    screen_bounds, list_option, window_id, _image_options = args
    assert screen_bounds == mock_quartz.CGRectNull
    assert list_option == mock_quartz.kCGWindowListOptionIncludingWindow
    assert window_id == 42


def test_capture_image_returns_pil_image_of_expected_size():
    mock_quartz = _mock_quartz(width=4, height=3)
    with patch.dict("sys.modules", {"Quartz": mock_quartz}):
        from drawing_coach._backend_macos import MacOSBackend

        img = MacOSBackend().capture_image(1)

    assert isinstance(img, Image.Image)
    assert img.size == (4, 3)


def test_capture_image_strips_row_padding():
    # bytes_per_row has 4 extra padding bytes per row beyond width*bpp
    mock_quartz = _mock_quartz(width=2, height=2, bytes_per_row=2 * 4 + 4)
    with patch.dict("sys.modules", {"Quartz": mock_quartz}):
        from drawing_coach._backend_macos import MacOSBackend

        img = MacOSBackend().capture_image(1)

    assert img.size == (2, 2)


def test_capture_image_returns_none_when_no_image():
    mock_quartz = _mock_quartz(image_ref=None)
    with patch.dict("sys.modules", {"Quartz": mock_quartz}):
        from drawing_coach._backend_macos import MacOSBackend

        assert MacOSBackend().capture_image(1) is None


def test_capture_image_returns_none_for_zero_size():
    mock_quartz = _mock_quartz(width=0, height=0)
    with patch.dict("sys.modules", {"Quartz": mock_quartz}):
        from drawing_coach._backend_macos import MacOSBackend

        assert MacOSBackend().capture_image(1) is None
