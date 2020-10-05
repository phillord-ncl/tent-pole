import canvasapi
import click
import os
import stringcase
import toml

from . import config
from . import course

def canvasname_from_path(filename):
    return os.path.splitext(
        os.path.basename(filename)
    )[0]

def __canvastitle_from_canvasname(canvasname):
    return stringcase.titlecase(canvasname)

def __canvastitle_from_path(filename):
    return __canvas_title_from_canvasname(__canvasname_from_path(filename))

def __page_exists(course, canvasname):
    pages = course.get_pages()
    canvastitle = __canvastitle_from_canvasname(canvasname)
    for page in pages:
        if page.title==canvastitle:
            return True

    return False

def __create_page(course,canvastitle):
    return course.create_page(
        wiki_page = {
            "title": canvastitle
        }
    )

def __get_create_page(course, canvasname):
    if not __page_exists(course, canvasname):
        __create_page(course,__canvastitle_from_canvasname(canvasname))

    return course.get_page(canvasname)

def page_by_title(pagetitle):
    try:
        return next(page for page
                in course.course_obj().get_pages()
                if pagetitle in page.title)
    except:
        return None

def page_by_guess(pageurl):
    return (
        " " not in pageurl
        and
        config.config_canvas().get_course(config.config_course()).get_page(pageurl)
        or
        page_by_title(pageurl)
    )

def page_obj():
    return page_by_guess(config.config_page())

## Errors
class PageExistsError(Exception):
    def __init__(self, course, canvastitle, message="Page Exists"):
        self.course = course.course_code
        self.canvastitle = canvastitle

        super().__init__("Page Exists: {} @ {}"
                         .format(self.canvastitle, self.course))

## CLI
@click.group()
def page():
    pass

@page.command(help="Return information about a page")
@click.argument("pageurl")
def data(pageurl):
    page = page_by_guess(pageurl)
    print(page)

@page.command(help="Create a page that does not exist")
@click.argument("filename")
def create(filename):
    course = config.config_canvas().get_course(config.config_course())
    canvasname = canvasname_from_path(filename)
    canvastitle = __canvastitle_from_canvasname(canvasname)

    if __page_exists(course, canvasname):
        raise PageExistsError(course, canvastitle)

    return __create_page(course, canvastitle)

@page.command(help="Dump information to a local file.")
@click.argument("filename")
def dump(filename):
    with open(os.path.splitext(filename)[0] + ".tpp", "w") as fh:
        ## Nothing to say at the moment
        toml.dump({},fh)

@page.command(help="Update an existing page that exists")
@click.argument("filename")
def update(filename):
    with open(filename) as fh: body = fh.read()
    course = config.config_canvas().get_course(config.config_course())
    page = course.get_page(canvasname_from_path(filename))
    page.edit(
        wiki_page={
            "body":body
        }
    )

@page.command(help="Create or Update a page")
@click.argument("filename")
def push(filename):
    with open(filename) as fh: body = fh.read()
    courseobj = course.course_obj()
    canvasname = canvasname_from_path(filename)
    page = __get_create_page(courseobj, canvasname)
    page.edit (
        wiki_page = {
            "body": body
        }
    )
    print("Pushed:{} as {}".format(filename, canvasname))
