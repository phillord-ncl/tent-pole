import os

import pytest

from tent_pole import quiz_parser

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "quiz")


def _parse(name):
    cwd = os.getcwd()
    os.chdir(FIXTURES)
    try:
        return quiz_parser.parse(name)
    finally:
        os.chdir(cwd)


def test_week1_quiz_front_matter_drops_points_possible(capsys):
    result = _parse("week1-quiz.quiz.md")
    assert result.quiz_kwargs == {
        "allowed_attempts": "1",
        "quiz_type": "graded_survey",
        "title": "Week 1 Quiz",
    }
    assert "points_possible" not in result.quiz_kwargs
    assert "dropping points_possible" in capsys.readouterr().err


def test_week1_quiz_has_no_preamble():
    result = _parse("week1-quiz.quiz.md")
    assert result.preamble_html == ""


def test_week1_quiz_three_ungrouped_questions():
    result = _parse("week1-quiz.quiz.md")
    assert len(result.items) == 3
    assert all(isinstance(item, quiz_parser.Question) for item in result.items)

    q1, q2, essay = result.items

    assert q1.question_name == "List comprehension output"
    assert q1.question_type == "multiple_choice_question"
    assert q1.points_possible == "1"
    weights = {a["answer_weight"] for a in q1.answers}
    assert weights == {0, 100}
    assert sum(1 for a in q1.answers if a["answer_weight"] == 100) == 1
    assert len(q1.answers) == 4

    assert q2.question_name == "Division by zero"
    assert q2.question_type == "multiple_choice_question"
    assert len(q2.answers) == 4
    assert sum(1 for a in q2.answers if a["answer_weight"] == 100) == 1

    assert essay.question_name == "Explaining ZeroDivisionError"
    assert essay.question_type == "essay_question"
    assert essay.answers == []


def test_week1_quiz_code_block_uses_pygments_inline_style_not_pandoc_classes():
    result = _parse("week1-quiz.quiz.md")
    q2 = result.items[1]
    assert "style=\"color:" in q2.question_text or "style=\"background:" in q2.question_text
    assert "sourceCode" not in q2.question_text


def test_question_groups_quiz_preamble():
    result = _parse("question-groups-quiz.quiz.md")
    assert "test" in result.preamble_html
    assert "Answer the questions" in result.preamble_html


def test_question_groups_quiz_structure():
    result = _parse("question-groups-quiz.quiz.md")
    assert len(result.items) == 2
    assert all(isinstance(item, quiz_parser.Group) for item in result.items)

    populated, empty = result.items

    assert populated.name == "Simple Questions to get Going"
    assert populated.pick_count == "1"
    assert populated.question_points == "1"
    assert len(populated.questions) == 1
    q = populated.questions[0]
    assert q.question_name == "Hello World (title)"
    assert q.question_type == "multiple_choice_question"
    correct = [a for a in q.answers if a["answer_weight"] == 100]
    assert len(correct) == 1
    assert "hello world" in correct[0]["answer_text"]

    ## The load-bearing case: an empty group must still be produced,
    ## with its own pick_count/question_points intact -- this is the
    ## real Canvas quirk (an empty group still inflates the quiz's
    ## question_count/points_possible) that motivated this design.
    assert empty.name == "Is this a group that actually exists?"
    assert empty.pick_count == "1"
    assert empty.question_points == "1"
    assert empty.questions == []


def test_essay_without_explicit_type_raises():
    import tempfile

    source = (
        "## No type here {.question}\n\n"
        "Just prose, no checkboxes, no type= attribute.\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".quiz.md", dir=FIXTURES, delete=False
    ) as fh:
        fh.write(source)
        path = os.path.basename(fh.name)
    try:
        with pytest.raises(quiz_parser.QuizParseError, match="No type here"):
            _parse(path)
    finally:
        os.remove(os.path.join(FIXTURES, path))
