import canvasapi
import click

from . import config

def __get_courses(canvas=None):
    return (canvas or config.config_canvas()).get_courses()


def course_by_name(coursename, canvas=None):
    ## getattr defaults, not course.name directly: a Canvas
    ## restricted-access course is returned by get_courses() as a stub
    ## with only {id, access_restricted_by_date}, no name -- confirmed
    ## on a real account, see course_by_exact for the same pattern.
    ## A falsy coursename (e.g. config_course() finding nothing
    ## configured) must return None immediately -- `None in "..."`
    ## raises TypeError, and an empty string would match every course.
    if not coursename:
        return None
    matches = [
        c for c in __get_courses(canvas)
        if coursename in getattr(c, "name", "")
    ]
    if len(matches) > 1:
        ## course_by_exact raises on this same ambiguity for
        ## config-driven lookups, where certainty matters more than
        ## convenience. This substring fallback is for interactive CLI
        ## use, where picking one and moving on is more useful than
        ## refusing outright -- but the choice should be visible, not
        ## silent, since which course it lands on depends on whatever
        ## order Canvas happened to return them in.
        click.echo(
            "Warning: {!r} matched {} courses, using the first: {}".format(
                coursename,
                len(matches),
                ", ".join(
                    "{} ({})".format(getattr(c, "name", "?"), getattr(c, "id", "?"))
                    for c in matches
                ),
            ),
            err=True,
        )
    return matches[0] if matches else None

def course_by_code(coursecode, canvas=None):
    ## A falsy coursecode must return None immediately -- otherwise
    ## `None == getattr(course, "course_code", None)` matches the
    ## first course lacking that attribute at all (e.g. a
    ## restricted-access stub), a confusing wrong-course match one
    ## step removed from "no course configured".
    if not coursecode:
        return None
    return next(
        (course for course in __get_courses(canvas)
         if coursecode == getattr(course, "course_code", None)),
        None
    )

class AmbiguousCourseIdentifier(Exception):
    def __init__(self, identifier, matches):
        self.identifier = identifier
        self.matches = matches
        super().__init__(
            "{!r} matched {} courses: {}".format(
                identifier,
                len(matches),
                ", ".join(
                    "{} ({})".format(
                        getattr(c, "name", "?"), getattr(c, "id", "?")
                    )
                    for c in matches
                ),
            )
        )

def course_by_exact(courseidentifier, canvas=None):
    """Like course_by_guess, but never guesses: an exact match on
    course_code or name only, and raises rather than silently picking one
    course out of several on an ambiguous identifier. Intended for
    config-driven lookups (e.g. [dev] test_course_id) where certainty
    matters more than typing convenience."""
    canvas = canvas or config.config_canvas()

    if str(courseidentifier).isnumeric():
        return canvas.get_course(courseidentifier)

    matches = [
        c for c in __get_courses(canvas)
        if courseidentifier == getattr(c, "course_code", None)
        or courseidentifier == getattr(c, "name", None)
    ]

    if len(matches) > 1:
        raise AmbiguousCourseIdentifier(courseidentifier, matches)

    return matches[0] if matches else None

def course_by_guess(courseidentifier, canvas=None):
    canvas = canvas or config.config_canvas()
    if str(courseidentifier).isnumeric():
        try:
            return canvas.get_course(courseidentifier)
        except canvasapi.exceptions.ResourceDoesNotExist:
            pass
    return (
        course_by_code(courseidentifier, canvas) or
        course_by_name(courseidentifier, canvas)
    )

def course_obj():
    return course_by_guess(config.config_course())

## CLI
@click.group()
def course():
    pass

@course.command(help="Return some information about a course")
@click.argument("courseidentifier")
def data(courseidentifier):
    course = course_by_guess(courseidentifier)

    print(course.__dict__)

@course.command(help="Return list of modules in a course")
@click.argument("courseidentifier")
def modules(courseidentifier):
    course = course_by_guess(courseidentifier)
    for i, module in enumerate(course.get_modules()):
        print(i+1, ":", module)

@course.command(help="Return list of files in a course")
@click.argument("courseidentifier")
def files(courseidentifier):
    course = course_by_guess(courseidentifier)
    for i, file in enumerate(course.get_files()):
        print(file, " (", file.id, ")", sep="")

# TODO could be collated? code dupliaction
@course.command(help="Return list of pages in a course")
@click.argument("courseidentifier")
def pages(courseidentifier):
    course = course_by_guess(courseidentifier)
    for i, page in enumerate(course.get_pages()):
        print(page)

@course.command(help="Return list of assignments in a course")
@click.argument("courseidentifier")
def assignments(courseidentifier):
    course = course_by_guess(courseidentifier)
    for i, assignment in enumerate(course.get_assignments()):
        print(assignment)

@course.command(help="Return list of quizzes in a course")
@click.argument("courseidentifier")
def quizzes(courseidentifier):
    course = course_by_guess(courseidentifier)
    for i, quiz in enumerate(course.get_quizzes()):
        print(quiz)

@course.command(help="Return list of discussion topics in a course")
@click.argument("courseidentifier")
def discussions(courseidentifier):
    course = course_by_guess(courseidentifier)
    for i, discussion in enumerate(course.get_discussion_topics()):
        print(discussion)
