import datetime

import pytest

from tent_pole import page

pytestmark = pytest.mark.canvas


def test_push_then_fetch_round_trip(sandbox_course):
    """Confirms tent-pole's push actually lands on Canvas as intended, by
    reading it straight back via the API afterwards -- no browser/login
    needed.

    The body includes a fresh timestamp on every run rather than a fixed
    string: with a fixed string, a silently failed edit() on a *second*
    run could still leave a *previous* run's successful content in place,
    and the assertion would pass anyway -- a false positive that says
    nothing about whether this run's push actually worked."""
    canvasname = "tent-pole-test-harness-page"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    body = "<p>tent-pole test harness round-trip check: {}</p>".format(timestamp)

    pushed = page.__get_create_page(sandbox_course, canvasname)
    pushed.edit(wiki_page={"body": body})

    fetched = sandbox_course.get_page(canvasname)

    assert body in fetched.body
