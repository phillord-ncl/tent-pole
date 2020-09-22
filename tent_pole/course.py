import click

from . import config

def __get_courses():
    return config.config_canvas().get_courses()

def course_by_name(coursename):
    return next(course for course in __get_courses()
                if coursename in course.name)

def course_by_guess(courseidentifier):
    return (
        courseidentifier.isnumeric()
        and
        config.config_canvas().get_course(courseidentifier)
        or
        course_by_name(courseidentifier)
    )

## CLI
@click.group()
def course():
    pass

@course.command(help="Return some information about a course")
@click.argument("courseidentifier")
def data(courseidentifier):
    course = course_by_guess(courseidentifier)

    print(course.__dict__)
