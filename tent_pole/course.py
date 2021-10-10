import click

from . import config

def __get_courses():
    return config.config_canvas().get_courses()


def course_by_name(coursename):
    return next(course for course in __get_courses()
                if coursename in course.name)

def course_by_code(coursecode):
    return next(course for course in __get_courses()
                if coursecode == course.course_code)

def course_by_guess(courseidentifier):
    return (
        courseidentifier.isnumeric()
        and
        config.config_canvas().get_course(courseidentifier)
        or
        course_by_code(courseidentifier)
        or
        course_by_name(courseidentifier)
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
