import os

import pytest
import toml
from click.testing import CliRunner

from tent_pole import course_import


class FakePage:
    def __init__(self, url, body="<p>hi</p>"):
        self.url = url
        self.body = body


class FakeModuleItem:
    def __init__(self, type, page_url=None, title=None, content_id=None,
                 indent=0, position=1):
        self.type = type
        self.page_url = page_url
        self.title = title
        self.content_id = content_id
        self.indent = indent
        self.position = position


class FakeModule:
    def __init__(self, name, items):
        self.name = name
        self._items = items

    def get_module_items(self):
        return self._items


class FakeCourse:
    def __init__(self, id=1, name="Test Course", modules=(), pages=()):
        self.id = id
        self.name = name
        self._modules = list(modules)
        self._pages = {p.url: p for p in pages}

    def get_modules(self):
        return self._modules

    def get_pages(self):
        return list(self._pages.values())

    def get_page(self, url):
        return self._pages[url]


@pytest.fixture(autouse=True)
def no_ambient_git_dir(monkeypatch):
    monkeypatch.delenv("GIT_DIR", raising=False)
    monkeypatch.delenv("GIT_WORK_TREE", raising=False)


def invoke(tmp_path, monkeypatch, fake_course, args):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(course_import.course, "course_by_guess", lambda ident: fake_course)
    return CliRunner().invoke(course_import.import_command, args)


def test_no_course_found_is_a_clean_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(course_import.course, "course_by_guess", lambda ident: None)

    result = CliRunner().invoke(course_import.import_command, ["999", "out"])

    assert result.exit_code != 0
    assert "No course found" in result.output


def test_refuses_a_nonempty_target_directory(tmp_path, monkeypatch):
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "existing.txt").write_text("keep me")
    fake_course = FakeCourse()

    result = invoke(tmp_path, monkeypatch, fake_course, ["1", "out"])

    assert result.exit_code != 0
    assert "already exists" in result.output
    assert (tmp_path / "out" / "existing.txt").read_text() == "keep me"


def test_default_directory_is_slugified_course_name(tmp_path, monkeypatch):
    fake_course = FakeCourse(name="My Great Course!")

    result = invoke(tmp_path, monkeypatch, fake_course, ["1"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "my-great-course").exists()


def test_orphaned_page_written_at_project_root(tmp_path, monkeypatch):
    fake_course = FakeCourse(pages=[FakePage("hello", "<p>Hello</p>")])

    result = invoke(tmp_path, monkeypatch, fake_course, ["1", "out"])

    assert result.exit_code == 0, result.output
    assert "Hello" in (tmp_path / "out" / "hello.md").read_text()


def test_module_page_written_into_its_own_slugified_subdirectory(tmp_path, monkeypatch):
    page = FakePage("intro", "<p>Intro content</p>")
    item = FakeModuleItem("Page", page_url="intro", indent=0, position=1)
    fake_course = FakeCourse(
        modules=[FakeModule("Week 1: Basics", [item])],
        pages=[page],
    )

    result = invoke(tmp_path, monkeypatch, fake_course, ["1", "out"])

    assert result.exit_code == 0, result.output
    md = (tmp_path / "out" / "week-1-basics" / "intro.md").read_text()
    assert "Intro content" in md


def test_module_directory_gets_tent_pole_toml_and_makefile(tmp_path, monkeypatch):
    page1 = FakePage("intro")
    page2 = FakePage("second")
    items = [
        FakeModuleItem("Page", page_url="intro", indent=0, position=1),
        FakeModuleItem("Page", page_url="second", indent=1, position=2),
    ]
    fake_course = FakeCourse(modules=[FakeModule("Week 1", items)], pages=[page1, page2])

    result = invoke(tmp_path, monkeypatch, fake_course, ["1", "out"])

    assert result.exit_code == 0, result.output
    moddir = tmp_path / "out" / "week-1"
    assert (moddir / "Makefile").exists()

    parsed = toml.load(moddir / "tent-pole.toml")
    assert parsed["module"]["identifier"] == "Week 1"
    ids = [item["id"] for item in parsed["module"]["items"]]
    assert ids == ["intro", "second"]
    assert parsed["module"]["items"][0].get("indent") is None
    assert parsed["module"]["items"][1]["indent"] == 1


def test_module_items_sorted_by_live_position_not_listing_order(tmp_path, monkeypatch):
    page1 = FakePage("first")
    page2 = FakePage("second")
    ## Deliberately out of order vs. position, to prove sorting happens.
    items = [
        FakeModuleItem("Page", page_url="second", position=2),
        FakeModuleItem("Page", page_url="first", position=1),
    ]
    fake_course = FakeCourse(modules=[FakeModule("Week 1", items)], pages=[page1, page2])

    result = invoke(tmp_path, monkeypatch, fake_course, ["1", "out"])

    assert result.exit_code == 0, result.output
    parsed = toml.load(tmp_path / "out" / "week-1" / "tent-pole.toml")
    ids = [item["id"] for item in parsed["module"]["items"]]
    assert ids == ["first", "second"]


def test_non_page_module_items_are_reported_not_silently_dropped(tmp_path, monkeypatch):
    page = FakePage("intro")
    items = [
        FakeModuleItem("Page", page_url="intro", position=1),
        FakeModuleItem("Quiz", title="A Quiz", content_id=42, position=2),
    ]
    fake_course = FakeCourse(modules=[FakeModule("Week 1", items)], pages=[page])

    result = invoke(tmp_path, monkeypatch, fake_course, ["1", "out"])

    assert result.exit_code == 0, result.output
    assert "Not imported" in result.output
    assert "Quiz" in result.output
    assert "A Quiz" in result.output


def test_module_with_no_page_items_gets_no_subdirectory(tmp_path, monkeypatch):
    items = [FakeModuleItem("SubHeader", title="Just a header", position=1)]
    fake_course = FakeCourse(modules=[FakeModule("Empty Week", items)])

    result = invoke(tmp_path, monkeypatch, fake_course, ["1", "out"])

    assert result.exit_code == 0, result.output
    assert not (tmp_path / "out" / "empty-week").exists()


def test_two_modules_with_colliding_slugs_get_disambiguated(tmp_path, monkeypatch):
    page1 = FakePage("a")
    page2 = FakePage("b")
    fake_course = FakeCourse(
        modules=[
            FakeModule("Week!", [FakeModuleItem("Page", page_url="a", position=1)]),
            FakeModule("Week?", [FakeModuleItem("Page", page_url="b", position=1)]),
        ],
        pages=[page1, page2],
    )

    result = invoke(tmp_path, monkeypatch, fake_course, ["1", "out"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / "week").exists()
    assert (tmp_path / "out" / "week-2").exists()


def test_root_tent_pole_toml_records_numeric_course_id(tmp_path, monkeypatch):
    fake_course = FakeCourse(id=16807, pages=[FakePage("hello")])

    result = invoke(tmp_path, monkeypatch, fake_course, ["1", "out"])

    assert result.exit_code == 0, result.output
    parsed = toml.load(tmp_path / "out" / "tent-pole.toml")
    assert parsed["course"]["id"] == "16807"


def test_root_makefile_recurses_into_module_subdirectories(tmp_path, monkeypatch):
    page = FakePage("intro")
    items = [FakeModuleItem("Page", page_url="intro", position=1)]
    fake_course = FakeCourse(modules=[FakeModule("Week 1", items)], pages=[page])

    result = invoke(tmp_path, monkeypatch, fake_course, ["1", "out"])

    assert result.exit_code == 0, result.output
    makefile = (tmp_path / "out" / "Makefile").read_text()
    assert "week-1" in makefile
    assert "$(MAKE) -C" in makefile


def test_git_init_runs_by_default(tmp_path, monkeypatch):
    fake_course = FakeCourse(pages=[FakePage("hello")])

    result = invoke(tmp_path, monkeypatch, fake_course, ["1", "out"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / ".git").exists()


def test_no_git_flag_skips_git_init(tmp_path, monkeypatch):
    fake_course = FakeCourse(pages=[FakePage("hello")])

    result = invoke(tmp_path, monkeypatch, fake_course, ["1", "out", "--no-git"])

    assert result.exit_code == 0, result.output
    assert not (tmp_path / "out" / ".git").exists()


def test_git_init_does_not_leak_cwd_into_the_calling_process(tmp_path, monkeypatch):
    """run_import temporarily chdirs into the new directory to reuse
    scaffold.git_init_unless_already_in_repo() unchanged -- must restore
    the caller's cwd (tmp_path, not tmp_path/out) afterwards regardless."""
    fake_course = FakeCourse(pages=[FakePage("hello")])

    invoke(tmp_path, monkeypatch, fake_course, ["1", "out"])

    assert os.path.realpath(os.getcwd()) == os.path.realpath(str(tmp_path))
