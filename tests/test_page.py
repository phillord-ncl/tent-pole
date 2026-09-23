import canvasapi.exceptions
import toml
from click.testing import CliRunner

from tent_pole import config, page


def test_canvasname_from_path_strips_directory_and_extension():
    assert page.canvasname_from_path("/a/b/test-1.html") == "test-1"


def test_canvasname_from_path_replaces_underscores_with_hyphens():
    assert page.canvasname_from_path("my_test_page.md") == "my-test-page"


def test_canvasname_from_path_no_extension():
    assert page.canvasname_from_path("README") == "README"


def test_canvastitle_leaves_all_caps_segment_alone():
    """Regression: stringcase.titlecase treats every capital-letter
    boundary as a new word when nothing else separates them, mangling
    README into "R E A D M E" -- confirmed live, 2026-09-09."""
    assert page.__canvastitle_from_canvasname("README") == "README"


def test_canvastitle_leaves_all_caps_segment_alone_among_others():
    assert (
        page.__canvastitle_from_canvasname("my-README-file")
        == "My README File"
    )


def test_canvastitle_still_titlecases_non_all_caps_segments():
    assert (
        page.__canvastitle_from_canvasname("comprehensions-and-operations")
        == "Comprehensions And Operations"
    )


class FakePage:
    def __init__(self, page_id=1, url="test-1", title="Test 1",
                 updated_at="2026-01-01T00:00:00Z", last_edited_by=None,
                 body="<p>hello</p>"):
        self.page_id = page_id
        self.url = url
        self.title = title
        self.updated_at = updated_at
        self.last_edited_by = last_edited_by
        self.body = body

    def edit(self, wiki_page):
        self.body = wiki_page["body"]


class FakeCourseForPage:
    def __init__(self, page_obj):
        self._page = page_obj

    def get_page(self, canvasname):
        return self._page


def write_local_file(path, content=b"<p>hello</p>"):
    path.write_bytes(content)
    return str(path)


## page_by_title / page_by_guess

class FakeCourseForLookup:
    def __init__(self, pages=None, get_page_result=None, get_page_raises=None):
        self._pages = pages or []
        self._get_page_result = get_page_result
        self._get_page_raises = get_page_raises

    def get_pages(self):
        return self._pages

    def get_page(self, url):
        if self._get_page_raises:
            raise self._get_page_raises
        return self._get_page_result


class FakeCanvasForLookup:
    def __init__(self, fake_course):
        self._fake_course = fake_course

    def get_course(self, course_id):
        return self._fake_course


def test_page_by_title_finds_matching_title(monkeypatch):
    target = FakePage(title="My Great Page")
    fake_course = FakeCourseForLookup(pages=[FakePage(title="Other"), target])
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)

    assert page.page_by_title("Great") is target


def test_page_by_title_returns_none_when_not_found(monkeypatch):
    """Regression test: page_by_title used to have a bare `except:`,
    catching everything (not just the expected StopIteration when
    next() finds nothing) and silently returning None either way --
    narrowed so a genuine bug isn't masked as "page not found"."""
    fake_course = FakeCourseForLookup(pages=[FakePage(title="Other")])
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)

    assert page.page_by_title("does not exist") is None


def test_page_by_guess_uses_get_page_directly_when_it_succeeds(monkeypatch):
    target = FakePage(title="Direct Hit")
    fake_course = FakeCourseForLookup(get_page_result=target)
    monkeypatch.setattr(config, "config_canvas", lambda: FakeCanvasForLookup(fake_course))
    monkeypatch.setattr(config, "config_course", lambda: "16807")

    assert page.page_by_guess("some-url") is target


def test_page_by_guess_falls_back_to_title_when_get_page_raises_not_found(monkeypatch):
    """Regression test: page_by_guess's "get_page(...) or
    page_by_title(...)" chain only ever fell through on a falsy return
    value -- a real 404 (ResourceDoesNotExist) crashed instead of
    trying the title-search fallback the "or" clearly intended."""
    target = FakePage(title="Found By Title")
    fake_course = FakeCourseForLookup(
        pages=[target],
        get_page_raises=canvasapi.exceptions.ResourceDoesNotExist("not found"),
    )
    monkeypatch.setattr(config, "config_canvas", lambda: FakeCanvasForLookup(fake_course))
    monkeypatch.setattr(config, "config_course", lambda: "16807")
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)

    assert page.page_by_guess("Found") is target


def test_page_by_guess_uses_title_search_when_url_has_a_space(monkeypatch):
    target = FakePage(title="Has A Space In It")
    fake_course = FakeCourseForLookup(pages=[target])
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)

    assert page.page_by_guess("Has A Space") is target


class _PageSummary:
    """What Canvas's list-pages endpoint actually returns: no .body
    attribute at all (unlike a single-page get_page result) -- a plain
    object rather than FakePage so accessing .body raises AttributeError
    exactly like the real canvasapi Page would, instead of silently
    returning None."""
    def __init__(self, title, url):
        self.title = title
        self.url = url


def test_find_page_title_fallback_refetches_the_full_page(monkeypatch):
    """Regression: Canvas disambiguates a title/slug reused since a
    prior page was deleted with -2, -3, etc, so the real url can diverge
    from canvasname -- __find_page's title-search fallback used to
    return the list-endpoint's own summary object directly, which has
    no .body, crashing any caller (e.g. __compiled_at_drift) that reads
    the page's actual content."""
    summary = _PageSummary(title="Programming", url="programming-4")
    full = FakePage(title="Programming", url="programming-4")

    class FakeCourse:
        def get_page(self, url):
            if url == "programming-4":
                return full
            raise canvasapi.exceptions.ResourceDoesNotExist("not found")

        def get_pages(self):
            return [summary]

    assert page.__find_page(FakeCourse(), "programming") is full


def test_page_metadata_includes_hash_and_editor(tmp_path):
    local = write_local_file(tmp_path / "test-1.html")
    fake_page = FakePage(last_edited_by={"id": 5272, "display_name": "Phillip Lord"})

    data = page.__page_metadata(local, fake_page)

    assert data["hash"] == page.manifest.hash_file(local)
    assert data["page_id"] == 1
    assert data["last_edited_by"] == {"id": 5272, "display_name": "Phillip Lord"}


def test_page_metadata_compiled_at_none_when_no_marker(tmp_path):
    """Plain HTML with no canvas-filter marker -- nothing to compare
    against later, not a drift signal either way."""
    local = write_local_file(tmp_path / "test-1.html", b"<p>hello</p>")
    fake_page = FakePage()

    data = page.__page_metadata(local, fake_page)

    assert data["compiled_at"] is None


def test_page_metadata_extracts_compiled_at_marker(tmp_path):
    local = write_local_file(
        tmp_path / "test-1.html",
        b'<p>hi</p><span data-tent-pole="managed" data-compiled-at="2026-09-07T00:00:00+00:00"></span>',
    )
    fake_page = FakePage()

    data = page.__page_metadata(local, fake_page)

    assert data["compiled_at"] == "2026-09-07T00:00:00+00:00"


def test_page_metadata_handles_never_edited_page(tmp_path):
    """A freshly created page (title set, no body edit yet) has
    last_edited_by = None -- must not crash."""
    local = write_local_file(tmp_path / "test-1.html")
    fake_page = FakePage(last_edited_by=None)

    data = page.__page_metadata(local, fake_page)

    assert data["last_edited_by"] == {"id": None, "display_name": None}


def test_local_drift_none_when_unchanged(tmp_path):
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {"hash": page.manifest.hash_file(local)}

    assert page.__local_drift(local, recorded) is None


def test_local_drift_detects_changed_file(tmp_path):
    local_path = tmp_path / "test-1.html"
    local = write_local_file(local_path, b"<p>original</p>")
    recorded = {"hash": page.manifest.hash_file(local)}

    write_local_file(local_path, b"<p>edited</p>")

    assert page.__local_drift(local, recorded) is not None


def test_local_drift_flags_missing_recorded_hash(tmp_path):
    local = write_local_file(tmp_path / "test-1.html")

    assert page.__local_drift(local, {}) is not None


def test_remote_drift_none_when_editor_matches_recorded(tmp_path, monkeypatch):
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {"last_edited_by": {"id": 5272, "display_name": "Phillip Lord"}}
    fake_course = FakeCourseForPage(
        FakePage(last_edited_by={"id": 5272, "display_name": "Phillip Lord"})
    )
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)

    assert page.__remote_drift(local, recorded) == []


def test_remote_drift_detects_editor_change(tmp_path, monkeypatch):
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {"last_edited_by": {"id": 5272, "display_name": "Phillip Lord"}}
    fake_course = FakeCourseForPage(
        FakePage(last_edited_by={"id": 9999, "display_name": "A Colleague"})
    )
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)

    assert page.__remote_drift(local, recorded) != []


def test_remote_drift_falls_back_to_current_user_when_no_baseline(tmp_path, monkeypatch):
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {}  # no baseline last_edited_by recorded at all
    fake_course = FakeCourseForPage(
        FakePage(last_edited_by={"id": 9999, "display_name": "A Colleague"})
    )
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)
    monkeypatch.setattr(config, "config_current_user_id", lambda: 5272)

    assert page.__remote_drift(local, recorded) != []


def test_remote_drift_no_baseline_but_current_user_matches(tmp_path, monkeypatch):
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {}
    fake_course = FakeCourseForPage(
        FakePage(last_edited_by={"id": 5272, "display_name": "Phillip Lord"})
    )
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)
    monkeypatch.setattr(config, "config_current_user_id", lambda: 5272)

    assert page.__remote_drift(local, recorded) == []


def test_remote_drift_none_when_compiled_at_matches(tmp_path, monkeypatch):
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {
        "last_edited_by": {"id": 5272, "display_name": "Phillip Lord"},
        "compiled_at": "2026-09-07T00:00:00+00:00",
    }
    fake_course = FakeCourseForPage(FakePage(
        last_edited_by={"id": 5272, "display_name": "Phillip Lord"},
        body='<span data-compiled-at="2026-09-07T00:00:00+00:00"></span>',
    ))
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)

    assert page.__remote_drift(local, recorded) == []


def test_remote_drift_detects_compiled_at_mismatch(tmp_path, monkeypatch):
    """The case __editor_drift alone can't catch: tent-pole re-pushes an
    old, unrebuilt local file -- last_edited_by is still tent-pole's own
    identity, but the live content is a different build than recorded."""
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {
        "last_edited_by": {"id": 5272, "display_name": "Phillip Lord"},
        "compiled_at": "2026-09-07T00:00:00+00:00",
    }
    fake_course = FakeCourseForPage(FakePage(
        last_edited_by={"id": 5272, "display_name": "Phillip Lord"},
        body='<span data-compiled-at="2026-09-06T00:00:00+00:00"></span>',
    ))
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)

    assert page.__remote_drift(local, recorded) != []


def test_remote_drift_no_compiled_at_baseline_is_not_a_drift_signal(tmp_path, monkeypatch):
    """Page never went through canvas-filter (or predates this feature)
    -- no baseline to compare against, so this check contributes nothing,
    even though the live body happens to have no marker either."""
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {"last_edited_by": {"id": 5272, "display_name": "Phillip Lord"}}
    fake_course = FakeCourseForPage(FakePage(
        last_edited_by={"id": 5272, "display_name": "Phillip Lord"},
        body="<p>hello</p>",
    ))
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)

    assert page.__remote_drift(local, recorded) == []


def test_remote_drift_reports_both_editor_and_compiled_at_problems(tmp_path, monkeypatch):
    """Both signals firing at once must both be reported, not just
    whichever is checked first."""
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {
        "last_edited_by": {"id": 5272, "display_name": "Phillip Lord"},
        "compiled_at": "2026-09-07T00:00:00+00:00",
    }
    fake_course = FakeCourseForPage(FakePage(
        last_edited_by={"id": 9999, "display_name": "A Colleague"},
        body='<span data-compiled-at="2026-09-06T00:00:00+00:00"></span>',
    ))
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)

    problems = page.__remote_drift(local, recorded)
    assert len(problems) == 2


def test_push_records_local_state_as_part_of_the_same_call(tmp_path, monkeypatch):
    """Regression: push used to leave writing the .tpp record to a
    separate `dump` step (task_page_push ran them as two actions).
    Confirmed live against the CSC1034 integration sandbox: a failure
    between the two (Canvas returning a flaky error while the edit
    itself still went through, or the build's own recursive fan-out
    aborting for an unrelated page in between) left a successful push
    permanently unrecorded, so every retry re-tripped
    __compiled_at_drift against tent-pole's own prior push. push must
    write its own record in the same call as the edit, the same as
    quiz.py's push/__dump_tpq already does."""
    monkeypatch.chdir(tmp_path)
    local = write_local_file(tmp_path / "foo.html")
    fake_page = FakePage(url="foo", title="Foo")
    monkeypatch.setattr(page.course, "course_obj", lambda: FakeCourseForPage(fake_page))

    result = CliRunner().invoke(page.page, ["push", "foo.html"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    tppfile = tmp_path / "foo.tpp"
    assert tppfile.exists()
    recorded = toml.load(tppfile)
    assert recorded["page_id"] == fake_page.page_id
    assert recorded["hash"] == page.manifest.hash_file(local)


class FakeCourseGone:
    """Neither lookup finds anything -- simulates a page that used to
    exist (there's a local .tpp for it) but has since been deleted
    from Canvas independently of tent-pole."""
    def __init__(self, created_page):
        self._created_page = created_page

    def get_page(self, canvasname):
        raise canvasapi.exceptions.ResourceDoesNotExist("not found")

    def get_pages(self):
        return []

    def create_page(self, wiki_page):
        return self._created_page


def test_push_recreates_a_page_deleted_independently_of_tent_pole(tmp_path, monkeypatch):
    """Regression: a page removed from Canvas independently of
    tent-pole (confirmed live during an integration-test course
    reset) used to crash push with "No page found -- run push first"
    -- raised from inside its own optional drift pre-check via
    __resolve_page -- even though a plain push is exactly the right
    thing to do here: there is nothing live left to protect against
    overwriting, so it should just recreate the page."""
    monkeypatch.chdir(tmp_path)
    write_local_file(tmp_path / "foo.html")
    (tmp_path / "foo.tpp").write_text(
        'hash = "stale"\ncompiled_at = "2026-01-01T00:00:00+00:00"\n'
    )
    created = FakePage(page_id=99, url="foo", title="Foo")
    monkeypatch.setattr(page.course, "course_obj", lambda: FakeCourseGone(created))

    result = CliRunner().invoke(page.page, ["push", "foo.html"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "Pushed" in result.output
