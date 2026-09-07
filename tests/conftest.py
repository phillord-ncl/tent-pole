import pytest

from tent_pole import config, course


@pytest.fixture(scope="session")
def sandbox_course():
    missing = [
        key
        for key, value in (
            ("test_course_id", config.config_test_course_id()),
            ("test_api_url", config.config_test_api_url()),
        )
        if not value
    ]
    if missing:
        pytest.skip(
            "Missing [dev] {} in tent-pole.toml; skipping Canvas test "
            "(default target is a sandbox course, not live)".format(", ".join(missing))
        )

    canvas = config.config_test_canvas()
    identifier = config.config_test_course_id()
    try:
        resolved = course.course_by_exact(identifier, canvas=canvas)
    except course.AmbiguousCourseIdentifier as e:
        pytest.fail("[dev] test_course_id is ambiguous: {}".format(e))

    if resolved is None:
        pytest.fail(
            "[dev] test_course_id = {!r} did not resolve to a course "
            "on {}".format(identifier, config.config_test_api_url())
        )
    return resolved
