import canvasapi
import click
import os
import stringcase
import toml

from . import canvas_filter
from . import config
from . import course
from . import manifest

def canvasname_from_path(filename):
    return os.path.splitext(
        os.path.basename(filename)
    )[0].replace("_", "-")

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

def __tpp_path(filename):
    return os.path.splitext(filename)[0] + ".tpp"

def __local_compiled_at(filename):
    with open(filename) as fh:
        return canvas_filter.extract_compiled_at(fh.read())

def __page_metadata(filename, pageobj):
    edited_by = pageobj.last_edited_by or {}
    return {
        "hash": manifest.hash_file(filename),
        "compiled_at": __local_compiled_at(filename),
        "page_id": pageobj.page_id,
        "url": pageobj.url,
        "title": pageobj.title,
        "updated_at": pageobj.updated_at,
        "last_edited_by": {
            "id": edited_by.get("id"),
            "display_name": edited_by.get("display_name"),
        },
    }

def __load_tpp(filename):
    tppfile = __tpp_path(filename)
    if not os.path.exists(tppfile):
        raise click.ClickException(
            "No {} found -- run push and dump first".format(tppfile)
        )
    with open(tppfile) as fh:
        return toml.load(fh)

def __local_drift(filename, recorded):
    recorded_hash = recorded.get("hash")
    if recorded_hash is None:
        return "no hash recorded in {} -- push and dump again".format(__tpp_path(filename))
    if manifest.hash_file(filename) != recorded_hash:
        return "local file has changed since it was last pushed"
    return None

def __editor_drift(pageobj, recorded):
    current_edited_by = pageobj.last_edited_by or {}
    recorded_edited_by = recorded.get("last_edited_by") or {}

    if recorded_edited_by.get("id") is not None:
        if current_edited_by.get("id") != recorded_edited_by.get("id"):
            return "page's editor changed since the last push (was {}, now {})".format(
                recorded_edited_by.get("display_name"),
                current_edited_by.get("display_name"),
            )
        return None

    ## No baseline editor recorded (e.g. a .tpp from before this existed):
    ## fall back to checking the current editor is at least tent-pole's
    ## own identity.
    current_id = current_edited_by.get("id")
    if current_id is not None and current_id != config.config_current_user_id():
        return (
            "page was last edited by someone other than tent-pole ({}), "
            "and no baseline was recorded to compare against"
        ).format(current_edited_by.get("display_name"))
    return None

def __compiled_at_drift(pageobj, recorded):
    """Stronger than __editor_drift for pages pushed through
    canvas-filter: compares the compile-timestamp marker actually live on
    Canvas against the one recorded at the last push, so re-pushing an
    old, unrebuilt local file (still edited_by tent-pole, so
    __editor_drift alone wouldn't catch it) is still detected. No
    baseline (page never went through canvas-filter, or predates this
    feature) means nothing to compare -- not a drift signal either way."""
    recorded_compiled_at = recorded.get("compiled_at")
    if recorded_compiled_at is None:
        return None

    live_compiled_at = canvas_filter.extract_compiled_at(pageobj.body)
    if live_compiled_at != recorded_compiled_at:
        return (
            "live content's compiled-at marker doesn't match what was "
            "last pushed (recorded {}, live {})"
        ).format(recorded_compiled_at, live_compiled_at)
    return None

def __remote_drift(filename, recorded):
    """Returns a list (possibly empty) rather than a single optional
    problem, so an editor change and a compiled-at mismatch occurring
    together are both reported, not just whichever is checked first."""
    canvasname = canvasname_from_path(filename)
    pageobj = course.course_obj().get_page(canvasname)

    return [
        p for p in (
            __editor_drift(pageobj, recorded),
            __compiled_at_drift(pageobj, recorded),
        )
        if p
    ]

@page.command(help="Dump information to a local file.")
@click.argument("filename")
def dump(filename):
    canvasname = canvasname_from_path(filename)
    pageobj = course.course_obj().get_page(canvasname)
    with open(__tpp_path(filename), "w") as fh:
        toml.dump(__page_metadata(filename, pageobj), fh)

@page.command(help="Check whether the local file has changed since it was "
                    "last pushed. Local only, no network access.")
@click.argument("filename")
def check(filename):
    recorded = __load_tpp(filename)
    problem = __local_drift(filename, recorded)
    if problem:
        raise click.ClickException(problem)
    print("OK: {} unchanged since last push".format(filename))

@page.command(help="Check local and remote drift: whether the local file "
                    "has changed, and whether the page was edited on "
                    "Canvas by someone else since the last push.")
@click.argument("filename")
def verify(filename):
    recorded = __load_tpp(filename)
    local_problem = __local_drift(filename, recorded)
    problems = ([local_problem] if local_problem else []) + __remote_drift(filename, recorded)
    if problems:
        raise click.ClickException("; ".join(problems))
    print("OK: {} matches local and remote state".format(filename))

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
