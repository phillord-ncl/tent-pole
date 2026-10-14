import os

import click
import toml

from canvasapi.rubric import Rubric
from canvasapi.util import combine_kwargs

from . import course
from . import manifest


RUBRIC_TOML_SUFFIX = ".rubric.toml"


def __tpa_path(filename):
    """The .tpa stamp-file path for a .rubric.toml source -- same
    compound-suffix handling as quiz_paths.tpq_path, since ".rubric.toml"
    must be stripped as one unit, not os.path.splitext's single-extension
    stripping (which would only remove the final ".toml")."""
    if filename.endswith(RUBRIC_TOML_SUFFIX):
        return filename[: -len(RUBRIC_TOML_SUFFIX)] + ".tpa"
    return os.path.splitext(filename)[0] + ".tpa"


def load_rubric_toml(filename):
    """The parsed [assignment]/[[criteria]] structure of a .rubric.toml --
    public (unlike every other helper in this module) because other
    tools (arbiter, tent-peg) need read-only access to a rubric's
    own criteria/points without pushing anything, e.g. to check a local
    marking script stays consistent with what's defined here."""
    with open(filename) as fh:
        return toml.load(fh)


def __description_html(toml_path, description):
    """The assignment description is a path (relative to the
    .rubric.toml file itself) to a markdown page, already built to
    .html via the normal %.html: %.md pipeline (pandoc through
    canvas-filter) -- same convention as page.py's push, which also
    reads an already-built .html rather than compiling markdown
    itself."""
    html_path = os.path.join(
        os.path.dirname(toml_path), os.path.splitext(description)[0] + ".html"
    )
    with open(html_path) as fh:
        return fh.read()


def __find_assignment(courseobj, title):
    """The existing assignment for `title`, if any -- same
    insurance-against-duplicates reasoning as page.__find_page/
    quiz.__find_quiz: there is no lookup-by-title endpoint. Canvas's own
    field for this is "name", not "title" -- kept as "title" in
    tent-pole's own vocabulary (TOML, quiz.py) and translated at the
    canvasapi boundary instead."""
    return next((a for a in courseobj.get_assignments() if a.name == title), None)


def __get_create_assignment(courseobj, title, assignment):
    existing = __find_assignment(courseobj, title)
    if existing is not None:
        return existing
    payload = dict(assignment)
    payload["name"] = payload.pop("title")
    created = courseobj.create_assignment(assignment=payload)
    ## Canvas's assignment-create endpoint doesn't reliably honour
    ## assignment[published] -- confirmed live against the npl25
    ## Personal Sandbox on beta (2026-10-12): creating with
    ## published=false still came back published=true, while the
    ## identical field on a follow-up edit() took effect correctly
    ## (same request-encoding path both times, so this is Canvas's own
    ## create behaviour, not a tent-pole/canvasapi encoding bug). Force
    ## it explicitly as a follow-up edit so a freshly-created
    ## assessment never surfaces to students before intended.
    if "published" in payload and created.published != payload["published"]:
        created.edit(assignment={"published": payload["published"]})
    return created


def __criteria_payload(criteria):
    """Canvas's own docs (rubrics.html) only say rubric[criteria] is
    "an indexed Hash of RubricCriteria objects where the keys are
    integer ids", without saying whether that means array position or a
    caller-chosen id. Confirmed live against the npl25 Personal Sandbox
    on beta (2026-10-12): position (0, 1, 2, ...) works for both create
    and update -- Canvas assigns its own criterion/rating ids on the
    response regardless of what's sent, and those ids are NOT stable
    across an update (a rating's id changed on re-push during that same
    verification, with no edit to the rating itself beyond a sibling's
    description) -- confirming tent-pole must never try to track or
    reuse Canvas's own criterion/rating ids itself.

    tent-pole's own per-criterion/per-rating "id" in the source TOML is
    deliberately NOT sent here -- it is tent-pole's own stable key for a
    human editing the TOML across re-pushes, not Canvas's internal
    criterion/rating id."""
    return {
        str(i): {
            "description": c["description"],
            "long_description": c.get("long_description", ""),
            "points": c["points"],
            "ratings": {
                str(j): {
                    "description": r["description"],
                    "points": r["points"],
                }
                for j, r in enumerate(c.get("ratings", []))
            },
        }
        for i, c in enumerate(criteria)
    }


def __association_payload(assignmentobj, rubric_settings):
    return {
        "association_id": assignmentobj.id,
        "association_type": "Assignment",
        "purpose": "grading",
        "use_for_grading": True,
        **{
            k: v for k, v in rubric_settings.items()
            if k in ("hide_score_total",)
        },
    }


def __rubric_payload(title, criteria, rubric_settings):
    payload = {
        "title": rubric_settings.get("title", title + " Rubric"),
        "criteria": __criteria_payload(criteria),
    }
    if "free_form_criterion_comments" in rubric_settings:
        payload["free_form_criterion_comments"] = rubric_settings["free_form_criterion_comments"]
    return payload


def __update_rubric(courseobj, rubric_id, rubric_kwargs, association_kwargs):
    """No public canvasapi wrapper for this -- see
    canvasapi_potential_prs_todo.md. Same `self._requester.request(...)`
    idiom canvasapi's own Rubric.delete()/RubricAssessment.update() use
    internally, just not exposed as a method for this one case."""
    response = courseobj._requester.request(
        "PUT",
        "courses/{}/rubrics/{}".format(courseobj.id, rubric_id),
        _kwargs=combine_kwargs(rubric=rubric_kwargs, rubric_association=association_kwargs),
    )
    data = response.json()
    rubric_dict = data.get("rubric", data)
    rubric_dict.setdefault("course_id", courseobj.id)
    return Rubric(courseobj._requester, rubric_dict)


def __load_tpa(filename):
    tpafile = __tpa_path(filename)
    if not os.path.exists(tpafile):
        return None
    with open(tpafile) as fh:
        return toml.load(fh)


def __dump_tpa(filename, assignmentobj, rubric_id, rubric_association_id):
    data = {
        "hash": manifest.hash_file(filename),
        "assignment_id": assignmentobj.id,
        "html_url": assignmentobj.html_url,
        "rubric_id": rubric_id,
        "rubric_association_id": rubric_association_id,
    }
    with open(__tpa_path(filename), "w") as fh:
        toml.dump(data, fh)


def __is_live(assignmentobj, courseobj, rubric_id):
    """True if pushing again would destroy marking-linked data --
    either the assignment is published, a real submission already
    exists (not just Canvas's own per-student unsubmitted stub, which
    get_submissions() returns regardless), or the rubric already has at
    least one recorded RubricAssessment."""
    if assignmentobj.published:
        return True
    if any(s.submitted_at is not None for s in assignmentobj.get_submissions()):
        return True
    rubricobj = courseobj.get_rubric(rubric_id, include=["assessments"])
    return bool(getattr(rubricobj, "assessments", None))


## CLI
@click.group()
def rubric():
    pass


@rubric.command(help="Create or update an assignment and its rubric from "
                      "a .rubric.toml file")
@click.argument("filename")
@click.option("--force", is_flag=True, help="Push even if the assignment "
              "is published or has real submissions, or the rubric "
              "already has recorded assessments -- this can orphan "
              "marking-linked data.")
def push(filename, force):
    parsed = load_rubric_toml(filename)
    assignment = parsed["assignment"]
    criteria = parsed.get("criteria", [])
    rubric_settings = parsed.get("rubric", {})

    title = assignment.get("title")
    if not title:
        raise click.ClickException(
            "{} has no [assignment] title".format(filename)
        )

    courseobj = course.course_obj()
    recorded = __load_tpa(filename)

    assignment_payload = dict(assignment)
    assignment_payload["description"] = __description_html(
        filename, assignment["description"]
    )

    if recorded is not None:
        assignmentobj = courseobj.get_assignment(recorded["assignment_id"])
        if not force and __is_live(assignmentobj, courseobj, recorded["rubric_id"]):
            raise click.ClickException(
                "{!r} is published, has real submissions, or its rubric "
                "already has recorded assessments -- pushing again can "
                "orphan marking-linked data, use --force to proceed "
                "anyway".format(title)
            )
        edit_payload = dict(assignment_payload)
        edit_payload["name"] = edit_payload.pop("title")
        assignmentobj.edit(assignment=edit_payload)
        rubricobj = __update_rubric(
            courseobj,
            recorded["rubric_id"],
            __rubric_payload(title, criteria, rubric_settings),
            __association_payload(assignmentobj, rubric_settings),
        )
        ## RubricAssociation itself doesn't change on an update -- its
        ## id is already recorded, nothing else to re-fetch.
        rubric_association_id = recorded["rubric_association_id"]
    else:
        assignmentobj = __get_create_assignment(courseobj, title, assignment_payload)
        created = courseobj.create_rubric(
            rubric=__rubric_payload(title, criteria, rubric_settings),
            rubric_association=__association_payload(assignmentobj, rubric_settings),
        )
        rubricobj = created["rubric"]
        rubric_association_id = created["rubric_association"].id

    __dump_tpa(filename, assignmentobj, rubricobj.id, rubric_association_id)

    print("Pushed: {} as assignment {!r} (id {})".format(filename, title, assignmentobj.id))
    print("  rubric id {}, {} criteria".format(rubricobj.id, len(criteria)))
