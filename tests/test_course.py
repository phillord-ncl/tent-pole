import pytest

from tent_pole import course


class FakeCourse:
    def __init__(self, id, name, course_code):
        self.id = id
        self.name = name
        self.course_code = course_code


class RestrictedFakeCourse:
    """Mirrors what Canvas actually returns for a restricted-access
    course: only id and access_restricted_by_date, no name/course_code."""
    def __init__(self, id):
        self.id = id
        self.access_restricted_by_date = True


class FakeCanvas:
    def __init__(self, courses):
        self._courses = courses

    def get_courses(self):
        return self._courses

    def get_course(self, course_id):
        return next(c for c in self._courses if str(c.id) == str(course_id))


def make_canvas():
    return FakeCanvas([
        FakeCourse(16807, "npl25 Personal Sandbox", "npl25 Personal Sandbox"),
        FakeCourse(70344, "Programming Portfolio 1 - CSC1034", "CSC1034 (26/27)"),
    ])


def test_course_by_name_matches_substring():
    canvas = make_canvas()
    found = course.course_by_name("Personal Sandbox", canvas=canvas)
    assert found.id == 16807


def test_course_by_name_returns_none_when_not_found():
    canvas = make_canvas()
    assert course.course_by_name("does not exist", canvas=canvas) is None


def test_course_by_code_exact_match():
    canvas = make_canvas()
    found = course.course_by_code("CSC1034 (26/27)", canvas=canvas)
    assert found.id == 70344


def test_course_by_code_returns_none_when_not_found():
    canvas = make_canvas()
    assert course.course_by_code("NOPE", canvas=canvas) is None


def test_course_by_guess_numeric_id_as_string():
    canvas = make_canvas()
    found = course.course_by_guess("16807", canvas=canvas)
    assert found.id == 16807


def test_course_by_guess_numeric_id_as_int_does_not_crash():
    canvas = make_canvas()
    found = course.course_by_guess(16807, canvas=canvas)
    assert found.id == 16807


def test_course_by_guess_falls_back_to_name_when_code_misses():
    """Regression test: course_by_code used to raise StopIteration on a
    miss instead of returning None, so this fallback never used to run."""
    canvas = make_canvas()
    found = course.course_by_guess("Personal Sandbox", canvas=canvas)
    assert found.id == 16807


def make_canvas_with_duplicate_names():
    return FakeCanvas([
        FakeCourse(14565, "njw125 Personal Sandbox", "njw125 Personal Sandbox"),
        FakeCourse(15547, "nmd34 Personal Sandbox", "nmd34 Personal Sandbox"),
        FakeCourse(16807, "npl25 Personal Sandbox", "npl25 Personal Sandbox"),
    ])


def test_course_by_exact_numeric_id():
    canvas = make_canvas()
    found = course.course_by_exact(16807, canvas=canvas)
    assert found.id == 16807


def test_course_by_exact_exact_name_match():
    canvas = make_canvas()
    found = course.course_by_exact("npl25 Personal Sandbox", canvas=canvas)
    assert found.id == 16807


def test_course_by_exact_returns_none_when_not_found():
    canvas = make_canvas()
    assert course.course_by_exact("does not exist", canvas=canvas) is None


def test_course_by_exact_rejects_substring_match():
    """The whole point: course_by_exact must NOT do course_by_guess's
    substring-on-name matching -- "Personal Sandbox" alone should not
    resolve to any of these three courses."""
    canvas = make_canvas_with_duplicate_names()
    assert course.course_by_exact("Personal Sandbox", canvas=canvas) is None


def test_course_by_exact_raises_on_ambiguous_identifier():
    canvas = FakeCanvas([
        FakeCourse(1, "CSC1034", "CSC1034"),
        FakeCourse(2, "CSC1034", "CSC1034-DUP"),
    ])
    with pytest.raises(course.AmbiguousCourseIdentifier):
        course.course_by_exact("CSC1034", canvas=canvas)


def test_course_by_exact_skips_restricted_access_course_without_crashing():
    """Regression test for a real Canvas behaviour: a restricted-access
    course is returned by get_courses() with only id and
    access_restricted_by_date set, no name/course_code at all."""
    canvas = FakeCanvas([
        RestrictedFakeCourse(32443),
        FakeCourse(16807, "npl25 Personal Sandbox", "npl25 Personal Sandbox"),
    ])
    found = course.course_by_exact("npl25 Personal Sandbox", canvas=canvas)
    assert found.id == 16807
