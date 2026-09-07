import canvasapi.exceptions

from tent_pole import config, module


class FakeModule:
    def __init__(self, id=1, name="Module 1"):
        self.id = id
        self.name = name


class FakeCourseForModule:
    def __init__(self, modules=None, get_module_result=None, get_module_raises=None):
        self._modules = modules or []
        self._get_module_result = get_module_result
        self._get_module_raises = get_module_raises

    def get_modules(self):
        return self._modules

    def get_module(self, module_id):
        if self._get_module_raises:
            raise self._get_module_raises
        return self._get_module_result


class FakeCanvasForModule:
    def __init__(self, fake_course):
        self._fake_course = fake_course

    def get_course(self, course_id):
        return self._fake_course


def test_module_by_name_finds_matching_module(monkeypatch):
    target = FakeModule(name="Week 3")
    fake_course = FakeCourseForModule(modules=[FakeModule(name="Week 1"), target])
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)

    assert module.module_by_name("Week 3") is target


def test_module_by_name_returns_none_when_not_found(monkeypatch):
    """Regression test: module_by_name used to have a bare `except:`,
    catching everything rather than just the StopIteration next() raises
    on a miss -- narrowed so a genuine bug isn't silently treated as
    "module not found"."""
    fake_course = FakeCourseForModule(modules=[FakeModule(name="Week 1")])
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)

    assert module.module_by_name("does not exist") is None


def test_module_by_guess_uses_get_module_directly_when_numeric(monkeypatch):
    target = FakeModule(id=42)
    fake_course = FakeCourseForModule(get_module_result=target)
    monkeypatch.setattr(config, "config_canvas", lambda: FakeCanvasForModule(fake_course))
    monkeypatch.setattr(config, "config_course", lambda: "16807")

    assert module.module_by_guess("42") is target


def test_module_by_guess_falls_back_to_name_when_numeric_id_not_found(monkeypatch):
    """Regression test: module_by_guess's "get_module(...) or
    module_by_name(...)" chain used no exception handling at all, so a
    numeric identifier that just happens not to be a real module id
    crashed with canvasapi's raw ResourceDoesNotExist instead of trying
    the name-search fallback the "or" clearly intended."""
    target = FakeModule(name="42")
    fake_course = FakeCourseForModule(
        modules=[target],
        get_module_raises=canvasapi.exceptions.ResourceDoesNotExist("not found"),
    )
    monkeypatch.setattr(config, "config_canvas", lambda: FakeCanvasForModule(fake_course))
    monkeypatch.setattr(config, "config_course", lambda: "16807")
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)

    assert module.module_by_guess("42") is target


def test_module_by_guess_uses_name_search_when_not_numeric(monkeypatch):
    target = FakeModule(name="Week 5")
    fake_course = FakeCourseForModule(modules=[target])
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)

    assert module.module_by_guess("Week 5") is target
