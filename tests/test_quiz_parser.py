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


def test_question_types_quiz_front_matter_drops_points_possible(capsys):
    result = _parse("question-types-quiz.quiz.md")
    assert result.quiz_kwargs == {
        "allowed_attempts": "1",
        "quiz_type": "practice_quiz",
        "title": "Tent-Pole quiz: main markdown features, practice quiz",
    }


def test_question_types_quiz_preamble_describes_quiz_type():
    result = _parse("question-types-quiz.quiz.md")
    assert "Practice quiz" in result.preamble_html
    assert "quiz_type: practice_quiz" in result.preamble_html


def test_question_types_quiz_structure():
    result = _parse("question-types-quiz.quiz.md")
    assert len(result.items) == 3
    real, separate, empty = result.items
    assert all(isinstance(item, quiz_parser.Group) for item in result.items)

    assert real.name == "Real Questions"
    assert real.pick_count == "6"
    assert len(real.questions) == 6

    assert separate.name == "Separate Group"
    assert len(separate.questions) == 1
    assert separate.questions[0].question_name == "Mock Question in a Separate Group"

    ## The load-bearing case: an empty group must still be produced,
    ## with its own pick_count/question_points intact -- this is the
    ## real Canvas quirk (an empty group still inflates the quiz's
    ## question_count/points_possible) that motivated this design.
    assert empty.name == "Empty Group"
    assert empty.pick_count == "1"
    assert empty.question_points == "1"
    assert empty.questions == []


def test_question_types_quiz_mc_with_code():
    result = _parse("question-types-quiz.quiz.md")
    q = result.items[0].questions[0]
    assert q.question_name == "Multiple Choice Question with Code"
    assert q.question_type == "multiple_choice_question"
    assert len(q.answers) == 4
    assert sum(1 for a in q.answers if a["answer_weight"] == 100) == 1
    ## Real Pygments inline-style output, not pandoc's own class-based
    ## highlighting (confirmed live this session: the latter renders
    ## with no colour at all in Canvas's quiz view).
    assert "style=\"color:" in q.question_text or "style=\"background:" in q.question_text
    assert "sourceCode" not in q.question_text


def test_question_types_quiz_multiple_answers_inferred_from_checkbox_count():
    result = _parse("question-types-quiz.quiz.md")
    q = result.items[0].questions[1]
    assert q.question_name == "Multiple Answers Question"
    assert q.question_type == "multiple_answers_question"
    assert sum(1 for a in q.answers if a["answer_weight"] == 100) == 2


def test_question_types_quiz_essay_has_no_answers():
    result = _parse("question-types-quiz.quiz.md")
    q = result.items[0].questions[2]
    assert q.question_name == "Essay Question"
    assert q.question_type == "essay_question"
    assert q.answers == []


def test_question_types_quiz_include_without_output_has_no_extra_content():
    result = _parse("question-types-quiz.quiz.md")
    q = result.items[0].questions[3]
    assert q.question_name == "Multiple Choice Question with Included Code, No Output Shown"
    assert "Outputs:" not in q.question_text


def test_question_types_quiz_include_with_output_attribute():
    """Uses the real include=/output= boolean-flag mechanism (a single
    code block), not two separately-included files -- confirms
    CodeIncludeAttrs' own derived .out path is exercised."""
    result = _parse("question-types-quiz.quiz.md")
    q = result.items[0].questions[4]
    assert q.question_name == "Multiple Choice Question with Included Code and Output"
    assert "Outputs:" in q.question_text
    assert "1" in q.question_text and "25" in q.question_text


def test_question_types_quiz_include_with_crash_attribute():
    result = _parse("question-types-quiz.quiz.md")
    q = result.items[0].questions[5]
    assert q.question_name == "Multiple Choice Question with Included Code and Crash Output"
    assert "Crashes:" in q.question_text
    assert "ZeroDivisionError" in q.question_text


def test_question_groups_quiz_front_matter_describes_quiz_type():
    result = _parse("question-groups-quiz.quiz.md")
    assert result.quiz_kwargs["quiz_type"] == "assignment"
    assert result.quiz_kwargs["title"] == "Tent-Pole quiz: question groups, graded quiz"
    assert "graded quiz" in result.preamble_html
    assert "quiz_type: assignment" in result.preamble_html


def test_question_groups_quiz_structure():
    """Two groups, each with one real question -- unlike an empty
    group (demonstrated separately in question-types-quiz.quiz.md's
    "Empty Group"), a group with nothing in it has nothing for Canvas
    to show in the take-quiz preview, so this file demonstrates a
    populated second group instead."""
    result = _parse("question-groups-quiz.quiz.md")
    assert len(result.items) == 2
    assert all(isinstance(item, quiz_parser.Group) for item in result.items)

    first, second = result.items

    assert first.name == "Simple Questions to get Going"
    assert first.pick_count == "1"
    assert first.question_points == "1"
    assert len(first.questions) == 1
    q = first.questions[0]
    assert q.question_name == "Hello World (title)"
    assert q.question_type == "multiple_choice_question"
    correct = [a for a in q.answers if a["answer_weight"] == 100]
    assert len(correct) == 1
    assert "hello world" in correct[0]["answer_text"]

    assert second.name == "Is this a group that actually exists?"
    assert second.pick_count == "1"
    assert second.question_points == "1"
    assert len(second.questions) == 1
    q2 = second.questions[0]
    assert q2.question_name == "Goodbye World"
    correct2 = [a for a in q2.answers if a["answer_weight"] == 100]
    assert len(correct2) == 1
    assert "goodbye world" in correct2[0]["answer_text"]


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
