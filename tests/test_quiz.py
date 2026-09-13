import os

import toml
from click.testing import CliRunner

from tent_pole import quiz


SIMPLE_QUIZ_MD = """---
title: "Example Quiz"
---

## Only question {.question points="1"}

What is true?

- [x] This
- [ ] That
"""

GROUPED_QUIZ_MD = """---
title: "Grouped Quiz"
---

## A group {.group pick="1" points="1"}

### Only question {.question}

What is true?

- [x] This
- [ ] That

## Empty group {.group pick="1" points="1"}
"""

ESSAY_QUIZ_MD = """---
title: "Essay Quiz"
---

## An essay {.question type="essay"}

Explain something.
"""


class FakeQuizQuestion:
    def __init__(self, id, quizobj):
        self.id = id
        self._quiz = quizobj

    def delete(self):
        self._quiz.deleted_question_ids.append(self.id)


class FakeQuizGroup:
    def __init__(self, id, quizobj):
        self.id = id
        self._quiz = quizobj

    def delete(self):
        self._quiz.deleted_group_ids.append(self.id)


class FakeQuiz:
    def __init__(self, id=1, title="Example Quiz", published=False, has_submissions=False):
        self.id = id
        self.title = title
        self.published = published
        self.html_url = "https://example.test/courses/1/quizzes/{}".format(id)
        self.has_submissions = has_submissions
        self.create_question_calls = []
        self.create_question_group_calls = []
        self.edit_calls = []
        self.deleted_question_ids = []
        self.deleted_group_ids = []
        self._next_id = id * 1000

    def _next(self):
        self._next_id += 1
        return self._next_id

    def create_question(self, question):
        self.create_question_calls.append(question)
        return FakeQuizQuestion(self._next(), self)

    def create_question_group(self, quiz_groups):
        self.create_question_group_calls.append(quiz_groups[0])
        return FakeQuizGroup(self._next(), self)

    def get_question(self, question_id):
        return FakeQuizQuestion(question_id, self)

    def get_quiz_group(self, group_id):
        return FakeQuizGroup(group_id, self)

    def get_submissions(self):
        return [object()] if self.has_submissions else []

    def edit(self, quiz):
        self.edit_calls.append(quiz)


class FakeCourse:
    def __init__(self, existing=None):
        self._quiz = existing
        self.created_quiz_kwargs = None

    def get_quizzes(self):
        return [self._quiz] if self._quiz else []

    def create_quiz(self, quiz):
        self.created_quiz_kwargs = quiz
        self._quiz = FakeQuiz(id=999, title=quiz["title"])
        return self._quiz

    def get_quiz(self, quiz_id):
        return self._quiz


def write_quiz_md(tmp_path, content, name="example.quiz.md"):
    target = tmp_path / name
    target.write_text(content)
    return target


def write_tpq(path, quiz_id, question_ids, group_ids):
    with open(quiz.__tpq_path(str(path)), "w") as fh:
        toml.dump({
            "hash": "irrelevant",
            "quiz_id": quiz_id,
            "html_url": "https://example.test/courses/1/quizzes/{}".format(quiz_id),
            "question_ids": question_ids,
            "group_ids": group_ids,
        }, fh)


def test_first_push_creates_quiz_and_writes_tpq(tmp_path, monkeypatch):
    fake_course = FakeCourse()
    monkeypatch.setattr(quiz.course, "course_obj", lambda: fake_course)

    target = write_quiz_md(tmp_path, SIMPLE_QUIZ_MD)
    result = CliRunner().invoke(quiz.quiz, ["push", str(target)])

    assert result.exit_code == 0, result.output
    assert fake_course.created_quiz_kwargs["title"] == "Example Quiz"

    created_quiz = fake_course._quiz
    assert len(created_quiz.create_question_calls) == 1
    payload = created_quiz.create_question_calls[0]
    assert payload["question_type"] == "multiple_choice_question"
    weights = {a["answer_weight"] for a in payload["answers"]}
    assert weights == {0, 100}
    ## Real Canvas create input keys, confirmed live this session --
    ## never the read-back shape (text/weight). Both answer_text and
    ## answer_html on every answer, uniformly -- sending them
    ## unevenly across a list of answers garbles Canvas's Rails-style
    ## array form-encoding (confirmed live: fields from two different
    ## answers ended up merged into one).
    assert all(
        {"answer_text", "answer_html", "answer_weight"} <= a.keys()
        for a in payload["answers"]
    )

    tpq_path = quiz.__tpq_path(str(target))
    assert os.path.exists(tpq_path)
    dumped = toml.load(tpq_path)
    assert dumped["quiz_id"] == created_quiz.id
    assert dumped["html_url"] == created_quiz.html_url
    assert dumped["group_ids"] == []
    assert len(dumped["question_ids"]) == 1


def test_second_push_deletes_previously_recorded_questions_and_groups(tmp_path, monkeypatch):
    fake_quiz = FakeQuiz(id=1, title="Example Quiz")
    fake_course = FakeCourse(existing=fake_quiz)
    monkeypatch.setattr(quiz.course, "course_obj", lambda: fake_course)

    target = write_quiz_md(tmp_path, SIMPLE_QUIZ_MD)
    write_tpq(target, quiz_id=1, question_ids=[11, 12], group_ids=[21])

    result = CliRunner().invoke(quiz.quiz, ["push", str(target)])

    assert result.exit_code == 0, result.output
    assert fake_quiz.deleted_question_ids == [11, 12]
    assert fake_quiz.deleted_group_ids == [21]
    assert len(fake_quiz.create_question_calls) == 1


def test_empty_group_still_recorded_for_future_teardown(tmp_path, monkeypatch):
    fake_course = FakeCourse()
    monkeypatch.setattr(quiz.course, "course_obj", lambda: fake_course)

    target = write_quiz_md(tmp_path, GROUPED_QUIZ_MD)
    result = CliRunner().invoke(quiz.quiz, ["push", str(target)])

    assert result.exit_code == 0, result.output
    created_quiz = fake_course._quiz
    assert len(created_quiz.create_question_group_calls) == 2
    assert len(created_quiz.create_question_calls) == 1

    dumped = toml.load(quiz.__tpq_path(str(target)))
    assert len(dumped["group_ids"]) == 2


def test_essay_question_has_no_answers(tmp_path, monkeypatch):
    fake_course = FakeCourse()
    monkeypatch.setattr(quiz.course, "course_obj", lambda: fake_course)

    target = write_quiz_md(tmp_path, ESSAY_QUIZ_MD)
    result = CliRunner().invoke(quiz.quiz, ["push", str(target)])

    assert result.exit_code == 0, result.output
    payload = fake_course._quiz.create_question_calls[0]
    assert payload["question_type"] == "essay_question"
    assert payload["answers"] == []


def test_published_quiz_refuses_without_force(tmp_path, monkeypatch):
    fake_quiz = FakeQuiz(id=1, title="Example Quiz", published=True)
    fake_course = FakeCourse(existing=fake_quiz)
    monkeypatch.setattr(quiz.course, "course_obj", lambda: fake_course)

    target = write_quiz_md(tmp_path, SIMPLE_QUIZ_MD)
    write_tpq(target, quiz_id=1, question_ids=[11], group_ids=[])

    result = CliRunner().invoke(quiz.quiz, ["push", str(target)])

    assert result.exit_code != 0
    assert fake_quiz.deleted_question_ids == []
    assert fake_quiz.create_question_calls == []


def test_has_submissions_refuses_without_force(tmp_path, monkeypatch):
    fake_quiz = FakeQuiz(id=1, title="Example Quiz", has_submissions=True)
    fake_course = FakeCourse(existing=fake_quiz)
    monkeypatch.setattr(quiz.course, "course_obj", lambda: fake_course)

    target = write_quiz_md(tmp_path, SIMPLE_QUIZ_MD)
    write_tpq(target, quiz_id=1, question_ids=[11], group_ids=[])

    result = CliRunner().invoke(quiz.quiz, ["push", str(target)])

    assert result.exit_code != 0
    assert fake_quiz.deleted_question_ids == []


def test_force_overwrites_published_quiz(tmp_path, monkeypatch):
    fake_quiz = FakeQuiz(id=1, title="Example Quiz", published=True)
    fake_course = FakeCourse(existing=fake_quiz)
    monkeypatch.setattr(quiz.course, "course_obj", lambda: fake_course)

    target = write_quiz_md(tmp_path, SIMPLE_QUIZ_MD)
    write_tpq(target, quiz_id=1, question_ids=[11], group_ids=[])

    result = CliRunner().invoke(quiz.quiz, ["push", "--force", str(target)])

    assert result.exit_code == 0, result.output
    assert fake_quiz.deleted_question_ids == [11]
    assert len(fake_quiz.create_question_calls) == 1


def test_dry_run_touches_no_network(tmp_path, monkeypatch):
    def boom():
        raise AssertionError("course_obj() should not be called in --dry-run")
    monkeypatch.setattr(quiz.course, "course_obj", boom)

    target = write_quiz_md(tmp_path, SIMPLE_QUIZ_MD)
    result = CliRunner().invoke(quiz.quiz, ["push", "--dry-run", str(target)])

    assert result.exit_code == 0, result.output
    assert "Only question" in result.output
    assert not os.path.exists(quiz.__tpq_path(str(target)))
