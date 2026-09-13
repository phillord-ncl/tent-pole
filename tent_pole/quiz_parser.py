import io
import json
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, Optional

import panflute as pf

from . import canvas_filter

CHECKED = "☒"
UNCHECKED = "☐"

## Short-form type= attribute values a header can write, mapped to the
## real Canvas question_type string -- kept separate from question_type
## itself so the markdown stays terse (`type="essay"`, not
## `type="essay_question"`). An unrecognised value passes through
## unchanged, so a not-yet-aliased (or already-correct) Canvas type
## name still works.
TYPE_ALIASES = {
    "essay": "essay_question",
    "multiple_choice": "multiple_choice_question",
    "multiple_answers": "multiple_answers_question",
    "text_only": "text_only_question",
}


class QuizParseError(Exception):
    pass


@dataclass
class Question:
    """Field names match the Canvas quiz_questions API directly (see
    tent_pole/quiz.py), so building a create_question() payload is a
    plain dataclasses.asdict() with no translation layer."""
    question_name: str
    question_text: str
    question_type: str
    points_possible: Optional[str] = None
    answers: List[dict] = field(default_factory=list)


@dataclass
class Group:
    """Field names match create_question_group()'s quiz_groups[0]
    shape directly, `questions` aside (that's this parser's own
    grouping, not sent to Canvas as-is -- quiz.py creates the group
    first, then each question tagged with the returned group id)."""
    name: str
    pick_count: Optional[str] = None
    question_points: Optional[str] = None
    questions: List[Question] = field(default_factory=list)


@dataclass
class ParsedQuiz:
    quiz_kwargs: dict
    preamble_html: str
    items: list  # Group | Question, in document order


class _PendingGroup:
    def __init__(self, header):
        self.header = header
        self.questions = []


class _PendingQuestion:
    def __init__(self, header):
        self.header = header
        self.blocks = []


def render_html(blocks, api_version):
    """Render a slice of top-level blocks to Canvas-ready HTML, reusing
    canvas_filter's real, unmodified dispatcher -- not pandoc's own
    highlighter -- so a CodeBlock gets the same Pygments inline-style
    treatment a pushed page's code gets (confirmed live this session:
    pandoc's own class-based highlighting renders with no colour at
    all in Canvas's quiz view). Image/Link handling comes along for
    free from the same dispatcher."""
    newdoc = pf.Doc(*blocks, api_version=api_version)
    newdoc.walk(canvas_filter.canvas_filter)
    raw = json.dumps(newdoc.to_json())
    result = subprocess.run(
        ["pandoc", "-f", "json", "-t", "html"],
        input=raw, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def render_plain(blocks, api_version):
    """Plain-text rendering of the same blocks, for answer_text -- an
    answer's `text`/`html` are genuinely separate fields on Canvas
    (confirmed live this session), and sending only one of the two
    across a list of answers with heterogeneous keys garbles Canvas's
    Rails-style array form-encoding (confirmed live: it merged two
    answers' fields together). Every answer must carry the same keys,
    so this is always sent alongside render_html's own answer_html."""
    newdoc = pf.Doc(*blocks, api_version=api_version)
    raw = json.dumps(newdoc.to_json())
    result = subprocess.run(
        ["pandoc", "-f", "json", "-t", "plain"],
        input=raw, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _is_checkbox_item(item):
    if not item.content:
        return False
    first_block = item.content[0]
    if not isinstance(first_block, (pf.Plain, pf.Para)) or not first_block.content:
        return False
    first_inline = first_block.content[0]
    return isinstance(first_inline, pf.Str) and first_inline.text in (CHECKED, UNCHECKED)


def _is_checkbox_list(bulletlist):
    return bool(bulletlist.content) and _is_checkbox_item(bulletlist.content[0])


def _answer_from_item(item, api_version):
    block = item.content[0]
    inlines = list(block.content)
    weight = 100 if inlines[0].text == CHECKED else 0
    rest = inlines[1:]
    if rest and isinstance(rest[0], pf.Space):
        rest = rest[1:]
    rest_blocks = [pf.Plain(*rest)]
    return {
        "answer_text": render_plain(rest_blocks, api_version),
        "answer_html": render_html(rest_blocks, api_version),
        "answer_weight": weight,
    }


def _extract_answers(blocks, api_version):
    """(answers-or-None, remaining-blocks). The first top-level
    checkbox BulletList among `blocks` is the answer list; every other
    block is question text. None (not an empty list) when no checkbox
    list is present at all -- that distinction is what tells
    _question_type an essay/text-only question from a multiple-choice
    one with (degenerately) zero answers."""
    for i, block in enumerate(blocks):
        if isinstance(block, pf.BulletList) and _is_checkbox_list(block):
            answers = [_answer_from_item(item, api_version) for item in block.content]
            remaining = blocks[:i] + blocks[i + 1:]
            return answers, remaining
    return None, blocks


def _question_type(header, answers, question_name):
    explicit = header.attributes.get("type")
    if explicit:
        return TYPE_ALIASES.get(explicit, explicit)
    if answers is not None:
        num_correct = sum(1 for a in answers if a["answer_weight"] == 100)
        return "multiple_choice_question" if num_correct <= 1 else "multiple_answers_question"
    raise QuizParseError(
        "Question {!r} has no checkbox answers and no explicit "
        "type= attribute -- essay/text-only questions must write "
        "type= explicitly, it is never inferred".format(question_name)
    )


def _finalize_question(pending, api_version):
    header = pending.header
    name = pf.stringify(header)
    answers, remaining = _extract_answers(pending.blocks, api_version)
    return Question(
        question_name=name,
        question_text=render_html(remaining, api_version),
        question_type=_question_type(header, answers, name),
        points_possible=header.attributes.get("points"),
        answers=answers or [],
    )


def _finalize_group(pending, api_version):
    header = pending.header
    return Group(
        name=pf.stringify(header),
        pick_count=header.attributes.get("pick"),
        question_points=header.attributes.get("points"),
        questions=[_finalize_question(q, api_version) for q in pending.questions],
    )


def _split_items(doc):
    """(preamble_blocks, items): items is a list of _PendingGroup /
    _PendingQuestion (ungrouped), not yet rendered to HTML -- kept
    separate from finalization so render_html only ever runs once per
    question/group, after all of its content blocks are known."""
    preamble_blocks = []
    items = []
    current_group = None
    current_question = None
    seen_header = False

    def close_question():
        nonlocal current_question
        if current_question is not None:
            (current_group.questions if current_group else items).append(current_question)
            current_question = None

    def close_group():
        nonlocal current_group
        close_question()
        if current_group is not None:
            items.append(current_group)
            current_group = None

    for elem in doc.content:
        if isinstance(elem, pf.Header):
            seen_header = True
            if "group" in elem.classes:
                close_group()
                current_group = _PendingGroup(elem)
                continue
            if "question" in elem.classes:
                close_question()
                current_question = _PendingQuestion(elem)
                continue
            ## A plain header: closes any scope whose own header is at
            ## the same level or shallower, same as a real document's
            ## section boundaries would. Anything not closed keeps
            ## this header as ordinary content (e.g. a sub-heading
            ## used for formatting inside a long question).
            if current_question is not None and elem.level <= current_question.header.level:
                close_question()
            if current_group is not None and elem.level <= current_group.header.level:
                close_group()
            if current_question is None and current_group is None:
                continue
        if not seen_header:
            preamble_blocks.append(elem)
        elif current_question is not None:
            current_question.blocks.append(elem)
        elif isinstance(elem, pf.Header):
            ## A plain header that stayed open as content but has
            ## nothing open to attach to (e.g. directly under an open
            ## group, before any question) -- keep it visible as a
            ## stray-content warning rather than silently dropping it.
            print(
                "warning: quiz_parser: header {!r} ignored, not inside "
                "any question".format(pf.stringify(elem)),
                file=sys.stderr,
            )
        else:
            print(
                "warning: quiz_parser: content ignored, not inside any "
                "question: {!r}".format(pf.stringify(elem)[:60]),
                file=sys.stderr,
            )

    close_group()
    return preamble_blocks, items


def parse(path):
    result = subprocess.run(
        ["pandoc", "-t", "json", path], capture_output=True, check=True, text=True,
    )
    doc = pf.load(io.StringIO(result.stdout))

    quiz_kwargs = dict(doc.get_metadata())
    if "points_possible" in quiz_kwargs:
        print(
            "warning: quiz_parser: dropping points_possible from front "
            "matter -- Canvas computes it from questions/groups, it "
            "cannot be set directly",
            file=sys.stderr,
        )
        del quiz_kwargs["points_possible"]

    preamble_blocks, pending_items = _split_items(doc)
    preamble_html = render_html(preamble_blocks, doc.api_version) if preamble_blocks else ""

    items = [
        _finalize_group(item, doc.api_version) if isinstance(item, _PendingGroup)
        else _finalize_question(item, doc.api_version)
        for item in pending_items
    ]

    return ParsedQuiz(quiz_kwargs=quiz_kwargs, preamble_html=preamble_html, items=items)
