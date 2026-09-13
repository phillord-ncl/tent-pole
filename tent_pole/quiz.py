import dataclasses
import os

import click
import toml

from . import course
from . import manifest
from . import quiz_parser
from . import quiz_paths


def __tpq_path(filename):
    return quiz_paths.tpq_path(filename)


def __find_quiz(courseobj, title):
    """The existing quiz for `title`, if any -- there is no
    lookup-by-title endpoint, same situation as page.__find_page, and
    for the same reason: cheap insurance against creating a duplicate
    quiz if a .tpq file is ever lost."""
    return next((q for q in courseobj.get_quizzes() if q.title == title), None)


def __get_create_quiz(courseobj, title, quiz_kwargs):
    existing = __find_quiz(courseobj, title)
    if existing is not None:
        return existing
    payload = dict(quiz_kwargs)
    payload["title"] = title
    return courseobj.create_quiz(quiz=payload)


def __load_tpq(filename):
    tpqfile = __tpq_path(filename)
    if not os.path.exists(tpqfile):
        return None
    with open(tpqfile) as fh:
        return toml.load(fh)


def __dump_tpq(filename, quizobj, question_ids, group_ids):
    data = {
        "hash": manifest.hash_file(filename),
        "quiz_id": quizobj.id,
        "html_url": quizobj.html_url,
        "question_ids": question_ids,
        "group_ids": group_ids,
    }
    with open(__tpq_path(filename), "w") as fh:
        toml.dump(data, fh)


def __is_live(quizobj):
    """True if pushing again would destroy submission-linked data --
    either the quiz is published, or it already has at least one
    submission (checked even for an unpublished quiz, since a quiz can
    be unpublished again after having collected submissions)."""
    if quizobj.published:
        return True
    return any(True for _ in quizobj.get_submissions())


def __create_question(quizobj, question, group_id):
    payload = {k: v for k, v in dataclasses.asdict(question).items() if v is not None}
    if group_id is not None:
        payload["quiz_group_id"] = group_id
    created = quizobj.create_question(question=payload)
    return created.id


def __push_items(quizobj, items):
    """(question_ids, group_ids), in creation order. An empty group
    still gets its id recorded -- canvasapi has no "list groups on a
    quiz" call, so a stamp-recorded id is the only way a future push
    can find it again to tear it down."""
    question_ids = []
    group_ids = []
    for item in items:
        if isinstance(item, quiz_parser.Group):
            payload = {
                k: v for k, v in dataclasses.asdict(item).items()
                if k != "questions" and v is not None
            }
            created_group = quizobj.create_question_group(quiz_groups=[payload])
            group_ids.append(created_group.id)
            for q in item.questions:
                question_ids.append(__create_question(quizobj, q, created_group.id))
        else:
            question_ids.append(__create_question(quizobj, item, None))
    return question_ids, group_ids


def __print_dry_run(parsed):
    print("Quiz kwargs:", parsed.quiz_kwargs)
    if parsed.preamble_html:
        print("Preamble:", parsed.preamble_html)
    for item in parsed.items:
        if isinstance(item, quiz_parser.Group):
            print("Group: {!r} (pick={}, points={})".format(
                item.name, item.pick_count, item.question_points
            ))
            for q in item.questions:
                print("  Question: {!r} [{}] {} answer(s)".format(
                    q.question_name, q.question_type, len(q.answers)
                ))
        else:
            print("Question: {!r} [{}] {} answer(s)".format(
                item.question_name, item.question_type, len(item.answers)
            ))


## CLI
@click.group()
def quiz():
    pass


@quiz.command(help="Create or update a quiz from a .quiz.md file")
@click.argument("filename")
@click.option("--force", is_flag=True, help="Push even if the quiz is "
              "published or has submissions -- this destroys "
              "submission-linked question/answer data.")
@click.option("--dry-run", is_flag=True, help="Parse and print the "
              "quiz structure without touching Canvas.")
def push(filename, force, dry_run):
    parsed = quiz_parser.parse(filename)

    if dry_run:
        __print_dry_run(parsed)
        return

    title = parsed.quiz_kwargs.get("title")
    if not title:
        raise click.ClickException(
            "{} has no 'title' in its front matter".format(filename)
        )

    courseobj = course.course_obj()
    recorded = __load_tpq(filename)

    if recorded is not None:
        quizobj = courseobj.get_quiz(recorded["quiz_id"])
        if not force and __is_live(quizobj):
            raise click.ClickException(
                "{!r} is published or has submissions -- pushing again "
                "will destroy submission-linked question/answer data, "
                "use --force to proceed anyway".format(title)
            )
        ## Questions individually, never relying on group-delete
        ## cascade -- canvasapi's QuizGroup.delete() gives no
        ## indication either way whether it cascades to member
        ## questions on Canvas's side.
        for qid in recorded.get("question_ids", []):
            quizobj.get_question(qid).delete()
        for gid in recorded.get("group_ids", []):
            quizobj.get_quiz_group(gid).delete()
    else:
        quizobj = __get_create_quiz(courseobj, title, parsed.quiz_kwargs)

    question_ids, group_ids = __push_items(quizobj, parsed.items)

    quiz_kwargs = dict(parsed.quiz_kwargs)
    quiz_kwargs["description"] = parsed.preamble_html
    quizobj.edit(quiz=quiz_kwargs)

    __dump_tpq(filename, quizobj, question_ids, group_ids)

    print("Pushed: {} as quiz {!r} (id {})".format(filename, title, quizobj.id))
    print("  {} question(s), {} group(s)".format(len(question_ids), len(group_ids)))
