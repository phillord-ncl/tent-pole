from tent_pole import page


def test_canvasname_from_path_strips_directory_and_extension():
    assert page.canvasname_from_path("/a/b/test-1.html") == "test-1"


def test_canvasname_from_path_replaces_underscores_with_hyphens():
    assert page.canvasname_from_path("my_test_page.md") == "my-test-page"


def test_canvasname_from_path_no_extension():
    assert page.canvasname_from_path("README") == "README"
