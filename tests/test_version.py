from drawing_coach._version import __version__


def test_version_is_non_empty_string():
    assert isinstance(__version__, str)
    assert len(__version__) > 0
