import canvasapi.exceptions
import toml
from click.testing import CliRunner

from tent_pole import config, module


class FakeModuleItem:
    def __init__(self, id, type, position, indent=0, page_url=None, content_id=None):
        self.id = id
        self.type = type
        self.position = position
        self.indent = indent
        self.page_url = page_url
        self.content_id = content_id
        self.edit_calls = []
        self.deleted = False

    def edit(self, **kwargs):
        self.edit_calls.append(kwargs)
        module_item = kwargs.get("module_item", {})
        if "position" in module_item:
            self.position = module_item["position"]
        if "indent" in module_item:
            self.indent = module_item["indent"]

    def delete(self):
        self.deleted = True


class FakeModule:
    def __init__(self, id=1, name="Module 1", items=None):
        self.id = id
        self.name = name
        self._items = list(items) if items else []
        self.create_module_item_calls = []

    def get_module_items(self):
        return list(self._items)

    def create_module_item(self, module_item):
        new_id = max([i.id for i in self._items], default=0) + 1
        item = FakeModuleItem(
            id=new_id,
            type=module_item["type"],
            position=module_item.get("position"),
            indent=module_item.get("indent", 0),
            page_url=module_item.get("page_url"),
            content_id=module_item.get("content_id"),
        )
        self._items.append(item)
        self.create_module_item_calls.append(module_item)
        return item


class FakeCourseForModule:
    def __init__(self, modules=None, get_module_result=None, get_module_raises=None):
        self._modules = modules or []
        self._get_module_result = get_module_result
        self._get_module_raises = get_module_raises
        self.created = None
        self.created_module = None

    def get_modules(self):
        return self._modules

    def get_module(self, module_id):
        if self._get_module_raises:
            raise self._get_module_raises
        return self._get_module_result

    def create_module(self, data):
        self.created = data
        self.created_module = FakeModule(name=data["name"])
        return self.created_module


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


## create -- like reorder, should work off tent-pole.toml with no
## argument, not just when a name is given explicitly.

def test_create_uses_explicit_modulename_when_given(monkeypatch):
    fake_course = FakeCourseForModule()
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)

    result = CliRunner().invoke(module.create, ["Week 9"])

    assert result.exit_code == 0, result.output
    assert fake_course.created == {"name": "Week 9"}
    assert "Created module: Week 9" in result.output


def test_create_defaults_to_config_module_when_no_argument(monkeypatch):
    fake_course = FakeCourseForModule()
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)
    monkeypatch.setattr(config, "config_module", lambda: "Week 1")

    result = CliRunner().invoke(module.create, [])

    assert result.exit_code == 0, result.output
    assert fake_course.created == {"name": "Week 1"}
    assert "Created module: Week 1" in result.output


def test_create_skips_when_a_module_with_that_name_already_exists(monkeypatch):
    """Idempotent: re-running create (e.g. part-1-prepare a second
    time) must not create a duplicate module of the same name."""
    fake_course = FakeCourseForModule(modules=[FakeModule(name="Week 1")])
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)

    result = CliRunner().invoke(module.create, ["Week 1"])

    assert result.exit_code == 0, result.output
    assert fake_course.created is None
    assert "Module already exists: Week 1" in result.output


def test_create_does_not_treat_a_prefix_match_as_already_existing(monkeypatch):
    """The existence check is an exact match, not module_by_name's
    substring search -- "Week 1" must not be satisfied by an existing
    "Week 10"."""
    fake_course = FakeCourseForModule(modules=[FakeModule(name="Week 10")])
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)

    result = CliRunner().invoke(module.create, ["Week 1"])

    assert result.exit_code == 0, result.output
    assert fake_course.created == {"name": "Week 1"}


## reorder -- get-or-create, then diff the item list against
## tent-pole.toml instead of deleting and recreating everything.

def test_reorder_creates_the_module_when_missing_then_its_items(monkeypatch):
    fake_course = FakeCourseForModule(modules=[])
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)
    monkeypatch.setattr(config, "config_module", lambda: "Week 1")
    monkeypatch.setattr(config, "config_module_items", lambda: [{"id": "introduction"}])

    result = CliRunner().invoke(module.reorder, [])

    assert result.exit_code == 0, result.output
    assert fake_course.created == {"name": "Week 1"}
    assert "Created module: Week 1" in result.output
    assert fake_course.created_module.create_module_item_calls == [
        {"type": "Page", "page_url": "introduction", "indent": "0", "position": 1}
    ]


def test_reorder_edits_an_existing_item_in_place_without_deleting(monkeypatch):
    """The whole point of the rewrite: an item that's already there,
    just needing a position/indent change, gets edit()'d -- same id,
    so any student completion state tracked against it survives --
    rather than being deleted and recreated."""
    existing = FakeModuleItem(id=99, type="Page", position=5, indent=0, page_url="introduction")
    fake_module = FakeModule(id=1, name="Week 1", items=[existing])
    fake_course = FakeCourseForModule(modules=[fake_module])
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)
    monkeypatch.setattr(config, "config_module", lambda: "Week 1")
    monkeypatch.setattr(config, "config_module_items",
                         lambda: [{"id": "introduction", "indent": 1}])

    result = CliRunner().invoke(module.reorder, [])

    assert result.exit_code == 0, result.output
    assert existing.deleted is False
    assert existing.edit_calls == [
        {"module_item": {"type": "Page", "page_url": "introduction", "indent": "1", "position": 1}}
    ]
    assert fake_module.create_module_item_calls == []


def test_reorder_leaves_an_already_correct_item_untouched(monkeypatch):
    existing = FakeModuleItem(id=99, type="Page", position=1, indent=0, page_url="introduction")
    fake_module = FakeModule(id=1, name="Week 1", items=[existing])
    fake_course = FakeCourseForModule(modules=[fake_module])
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)
    monkeypatch.setattr(config, "config_module", lambda: "Week 1")
    monkeypatch.setattr(config, "config_module_items", lambda: [{"id": "introduction"}])

    result = CliRunner().invoke(module.reorder, [])

    assert result.exit_code == 0, result.output
    assert existing.edit_calls == []
    assert existing.deleted is False


def test_reorder_deletes_a_live_item_not_in_config(monkeypatch):
    keep = FakeModuleItem(id=1, type="Page", position=1, indent=0, page_url="introduction")
    remove = FakeModuleItem(id=2, type="Page", position=2, indent=0, page_url="old-page")
    fake_module = FakeModule(id=1, name="Week 1", items=[keep, remove])
    fake_course = FakeCourseForModule(modules=[fake_module])
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)
    monkeypatch.setattr(config, "config_module", lambda: "Week 1")
    monkeypatch.setattr(config, "config_module_items", lambda: [{"id": "introduction"}])

    result = CliRunner().invoke(module.reorder, [])

    assert result.exit_code == 0, result.output
    assert keep.deleted is False
    assert remove.deleted is True


def test_reorder_silently_skips_a_config_item_of_unsupported_type(monkeypatch):
    """Matches the pre-rewrite behaviour: an item type reorder() has no
    branch for was (and still is) silently skipped, not an error."""
    fake_module = FakeModule(id=1, name="Week 1", items=[])
    fake_course = FakeCourseForModule(modules=[fake_module])
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)
    monkeypatch.setattr(config, "config_module", lambda: "Week 1")
    monkeypatch.setattr(config, "config_module_items",
                         lambda: [{"type": "SubHeader", "id": "x"}])

    result = CliRunner().invoke(module.reorder, [])

    assert result.exit_code == 0, result.output
    assert fake_module.create_module_item_calls == []


## dump -- resolved module state as TOML, for the tent-pole.toml.tpm
## staleness stamp.

def test_dump_prints_module_state_as_toml(monkeypatch):
    fake_module = FakeModule(id=7, name="Week 1", items=[])
    fake_course = FakeCourseForModule(modules=[fake_module])
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)
    monkeypatch.setattr(config, "config_module", lambda: "Week 1")
    monkeypatch.setattr(config, "config_module_items", lambda: [{"id": "introduction"}])

    result = CliRunner().invoke(module.dump, [])

    assert result.exit_code == 0, result.output
    parsed = toml.loads(result.output)
    assert parsed["module_id"] == 7
    assert parsed["name"] == "Week 1"
    assert "hash" in parsed


def test_dump_errors_when_module_not_found(monkeypatch):
    fake_course = FakeCourseForModule(modules=[])
    monkeypatch.setattr(module.course, "course_obj", lambda: fake_course)
    monkeypatch.setattr(config, "config_module", lambda: "Week 1")

    result = CliRunner().invoke(module.dump, [])

    assert result.exit_code != 0
    assert "not found" in result.output
