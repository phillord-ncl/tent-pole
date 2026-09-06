import pytest

from tent_pole import page

pytestmark = pytest.mark.canvas


def test_push_then_fetch_round_trip(sandbox_course):
    """Confirms tent-pole's push actually lands on Canvas as intended, by
    reading it straight back via the API afterwards -- no browser/login
    needed. See claude_redesign.md's Testing/verification section."""
    canvasname = "tent-pole-test-harness-page"
    body = "<p>tent-pole test harness round-trip check</p>"

    pushed = page.__get_create_page(sandbox_course, canvasname)
    pushed.edit(wiki_page={"body": body})

    fetched = sandbox_course.get_page(canvasname)

    assert body in fetched.body
