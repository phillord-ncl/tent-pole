import os

import toml
from click.testing import CliRunner

from tent_pole import rubric


SIMPLE_RUBRIC_TOML = """
[assignment]
title = "Exercise 2"
description = "description.md"
points_possible = 10
submission_types = ["online_upload"]
published = false

[[criteria]]
id = "correctness"
description = "Correctness"
points = 10

[[criteria.ratings]]
id = "full"
description = "Fully correct"
points = 10

[[criteria.ratings]]
id = "none"
description = "Incorrect"
points = 0
"""


class FakeSubmission:
    def __init__(self, submitted_at=None):
        self.submitted_at = submitted_at


class FakeAssignment:
    def __init__(self, id=1, name="Exercise 2", published=False, submissions=None):
        self.id = id
        self.name = name
        self.published = published
        self.html_url = "https://example.test/courses/1/assignments/{}".format(id)
        self._submissions = submissions or []
        self.edit_calls = []

    def get_submissions(self):
        return self._submissions

    def edit(self, assignment):
        self.edit_calls.append(assignment)
        if "published" in assignment:
            self.published = assignment["published"]


class FakeRubric:
    def __init__(self, id=1, assessments=None):
        self.id = id
        self.assessments = assessments or []


class FakeRubricAssociation:
    def __init__(self, id=1):
        self.id = id


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class FakeRequester:
    def __init__(self):
        self.put_calls = []

    def request(self, method, path, _kwargs=None):
        self.put_calls.append((method, path, _kwargs))
        return FakeResponse({"rubric": {"id": 1}})


class FakeCourse:
    def __init__(self, id=100, existing_assignment=None, existing_rubric=None):
        self.id = id
        self._assignment = existing_assignment
        self._rubric = existing_rubric or FakeRubric(id=1)
        self._requester = FakeRequester()
        self.create_assignment_calls = []
        self.create_rubric_calls = []

    def get_assignments(self):
        return [self._assignment] if self._assignment else []

    def create_assignment(self, assignment):
        self.create_assignment_calls.append(assignment)
        ## Mirrors Canvas's own confirmed-live quirk: a freshly created
        ## assignment comes back published=True regardless of what was
        ## sent, so rubric.py's own follow-up-edit workaround has
        ## something real to correct.
        self._assignment = FakeAssignment(id=999, name=assignment["name"], published=True)
        return self._assignment

    def get_assignment(self, assignment_id):
        return self._assignment

    def create_rubric(self, rubric, rubric_association):
        self.create_rubric_calls.append((rubric, rubric_association))
        return {
            "rubric": self._rubric,
            "rubric_association": FakeRubricAssociation(id=501),
        }

    def get_rubric(self, rubric_id, include=None):
        return self._rubric


def write_rubric_toml(tmp_path, content, name="example.rubric.toml"):
    target = tmp_path / name
    target.write_text(content)
    (tmp_path / "description.html").write_text("<p>Do the thing.</p>")
    return target


def write_tpa(path, assignment_id, rubric_id, rubric_association_id):
    with open(rubric.__tpa_path(str(path)), "w") as fh:
        toml.dump({
            "hash": "irrelevant",
            "assignment_id": assignment_id,
            "rubric_id": rubric_id,
            "rubric_association_id": rubric_association_id,
        }, fh)


def test_first_push_creates_assignment_and_rubric(tmp_path, monkeypatch):
    fake_course = FakeCourse()
    monkeypatch.setattr(rubric.course, "course_obj", lambda: fake_course)

    target = write_rubric_toml(tmp_path, SIMPLE_RUBRIC_TOML)
    result = CliRunner().invoke(rubric.rubric, ["push", str(target)])

    assert result.exit_code == 0, result.output
    assert fake_course.create_assignment_calls[0]["name"] == "Exercise 2"
    assert fake_course.create_rubric_calls[0][1]["association_id"] == 999


def test_first_push_corrects_publish_state_canvas_ignored_on_create(tmp_path, monkeypatch):
    """Canvas's create-assignment endpoint doesn't reliably honour
    assignment[published] -- confirmed live (see rubric.py's
    __get_create_assignment) -- so a freshly created assignment must
    come back matching the TOML's published=false, not Canvas's own
    create-time default."""
    fake_course = FakeCourse()
    monkeypatch.setattr(rubric.course, "course_obj", lambda: fake_course)

    target = write_rubric_toml(tmp_path, SIMPLE_RUBRIC_TOML)
    result = CliRunner().invoke(rubric.rubric, ["push", str(target)])

    assert result.exit_code == 0, result.output
    assert fake_course._assignment.published is False
    assert fake_course._assignment.edit_calls == [{"published": False}]

    tpa_path = rubric.__tpa_path(str(target))
    assert os.path.exists(tpa_path)
    dumped = toml.load(tpa_path)
    assert dumped["assignment_id"] == 999
    assert dumped["rubric_association_id"] == 501
    assert dumped["html_url"] == "https://example.test/courses/1/assignments/999"


def test_idempotent_repush_updates_in_place(tmp_path, monkeypatch):
    fake_assignment = FakeAssignment(id=1, name="Exercise 2")
    fake_course = FakeCourse(existing_assignment=fake_assignment)
    monkeypatch.setattr(rubric.course, "course_obj", lambda: fake_course)

    target = write_rubric_toml(tmp_path, SIMPLE_RUBRIC_TOML)
    write_tpa(target, assignment_id=1, rubric_id=1, rubric_association_id=501)

    result = CliRunner().invoke(rubric.rubric, ["push", str(target)])

    assert result.exit_code == 0, result.output
    assert len(fake_assignment.edit_calls) == 1
    assert fake_assignment.edit_calls[0]["name"] == "Exercise 2"
    assert len(fake_course._requester.put_calls) == 1
    assert fake_course.create_assignment_calls == []
    assert fake_course.create_rubric_calls == []


def test_published_assignment_refuses_without_force(tmp_path, monkeypatch):
    fake_assignment = FakeAssignment(id=1, name="Exercise 2", published=True)
    fake_course = FakeCourse(existing_assignment=fake_assignment)
    monkeypatch.setattr(rubric.course, "course_obj", lambda: fake_course)

    target = write_rubric_toml(tmp_path, SIMPLE_RUBRIC_TOML)
    write_tpa(target, assignment_id=1, rubric_id=1, rubric_association_id=501)

    result = CliRunner().invoke(rubric.rubric, ["push", str(target)])

    assert result.exit_code != 0
    assert fake_assignment.edit_calls == []
    assert fake_course._requester.put_calls == []


def test_real_submission_refuses_without_force(tmp_path, monkeypatch):
    fake_assignment = FakeAssignment(
        id=1, name="Exercise 2",
        submissions=[FakeSubmission(submitted_at="2026-10-01T00:00:00Z")],
    )
    fake_course = FakeCourse(existing_assignment=fake_assignment)
    monkeypatch.setattr(rubric.course, "course_obj", lambda: fake_course)

    target = write_rubric_toml(tmp_path, SIMPLE_RUBRIC_TOML)
    write_tpa(target, assignment_id=1, rubric_id=1, rubric_association_id=501)

    result = CliRunner().invoke(rubric.rubric, ["push", str(target)])

    assert result.exit_code != 0
    assert fake_assignment.edit_calls == []


def test_unsubmitted_stub_submission_does_not_block(tmp_path, monkeypatch):
    """Canvas's get_submissions() returns a stub per enrolled student
    even with nothing submitted -- only a real submitted_at should
    count as "live"."""
    fake_assignment = FakeAssignment(
        id=1, name="Exercise 2", submissions=[FakeSubmission(submitted_at=None)]
    )
    fake_course = FakeCourse(existing_assignment=fake_assignment)
    monkeypatch.setattr(rubric.course, "course_obj", lambda: fake_course)

    target = write_rubric_toml(tmp_path, SIMPLE_RUBRIC_TOML)
    write_tpa(target, assignment_id=1, rubric_id=1, rubric_association_id=501)

    result = CliRunner().invoke(rubric.rubric, ["push", str(target)])

    assert result.exit_code == 0, result.output


def test_existing_rubric_assessment_refuses_without_force(tmp_path, monkeypatch):
    fake_assignment = FakeAssignment(id=1, name="Exercise 2")
    fake_rubric = FakeRubric(id=1, assessments=[object()])
    fake_course = FakeCourse(existing_assignment=fake_assignment, existing_rubric=fake_rubric)
    monkeypatch.setattr(rubric.course, "course_obj", lambda: fake_course)

    target = write_rubric_toml(tmp_path, SIMPLE_RUBRIC_TOML)
    write_tpa(target, assignment_id=1, rubric_id=1, rubric_association_id=501)

    result = CliRunner().invoke(rubric.rubric, ["push", str(target)])

    assert result.exit_code != 0
    assert fake_assignment.edit_calls == []


def test_force_overwrites_published_assignment(tmp_path, monkeypatch):
    fake_assignment = FakeAssignment(id=1, name="Exercise 2", published=True)
    fake_course = FakeCourse(existing_assignment=fake_assignment)
    monkeypatch.setattr(rubric.course, "course_obj", lambda: fake_course)

    target = write_rubric_toml(tmp_path, SIMPLE_RUBRIC_TOML)
    write_tpa(target, assignment_id=1, rubric_id=1, rubric_association_id=501)

    result = CliRunner().invoke(rubric.rubric, ["push", "--force", str(target)])

    assert result.exit_code == 0, result.output
    assert len(fake_assignment.edit_calls) == 1
