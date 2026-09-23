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
    ## stringcase.titlecase treats every capital-letter boundary as a
    ## new word when nothing else separates them, mangling an
    ## all-caps, no-separator segment into single letters with spaces
    ## between (README -> "R E A D M E"). Leave such a segment as-is;
    ## every other segment (canvasname_from_path already replaced
    ## underscores with hyphens) still goes through titlecase exactly
    ## as before.
    return " ".join(
        segment if segment.isupper() else stringcase.titlecase(segment)
        for segment in canvasname.split("-")
    )

def __canvastitle_from_path(filename):
    return __canvas_title_from_canvasname(__canvasname_from_path(filename))

def __find_page(course, canvasname):
    """The existing page for canvasname, if any. Tries Canvas's own
    url lookup first (the common case, and all most callers/tests
    need), falling back to a title search only if that misses --
    Canvas disambiguates a title/slug that's ever been used before in
    the course (even by a page since deleted) with -2, -3, etc, so a
    page's real url can diverge from canvasname indefinitely once
    that's happened once, and only a title search still finds it.

    The title search re-fetches by url once a match is found rather
    than returning that match directly: Canvas's list-pages endpoint
    (unlike its single-page one) never populates .body, so a caller
    that needs the page's actual content -- __compiled_at_drift, in
    particular -- would crash with a bare AttributeError on a page
    that only ever needed the title-search path to be found."""
    try:
        return course.get_page(canvasname)
    except canvasapi.exceptions.ResourceDoesNotExist:
        pass
    canvastitle = __canvastitle_from_canvasname(canvasname)
    for page in course.get_pages():
        if page.title == canvastitle:
            return course.get_page(page.url)
    return None

def __page_exists(course, canvasname):
    return __find_page(course, canvasname) is not None

def __create_page(course,canvastitle):
    return course.create_page(
        wiki_page = {
            "title": canvastitle
        }
    )

def __get_create_page(course, canvasname):
    """The course's page for canvasname -- the actual Page object
    found or just created, never re-fetched by guessing its url from
    canvasname (see __find_page)."""
    existing = __find_page(course, canvasname)
    if existing is not None:
        return existing
    return __create_page(course, __canvastitle_from_canvasname(canvasname))

def __resolve_page(course, canvasname):
    """Like __get_create_page, but for the read/update-only commands
    below -- they need an existing page and should never create one,
    so a miss is a clear error rather than a silent create."""
    found = __find_page(course, canvasname)
    if found is None:
        raise click.ClickException(
            "No page found for {!r} -- run push first".format(canvasname)
        )
    return found

def page_by_title(pagetitle):
    try:
        return next(page for page
                in course.course_obj().get_pages()
                if pagetitle in page.title)
    except StopIteration:
        return None

def page_by_guess(pageurl):
    if " " not in pageurl:
        try:
            return course.course_obj().get_page(pageurl)
        except canvasapi.exceptions.ResourceDoesNotExist:
            pass
    return page_by_title(pageurl)

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
    courseobj = course.course_obj()
    canvasname = canvasname_from_path(filename)
    canvastitle = __canvastitle_from_canvasname(canvasname)

    if __page_exists(courseobj, canvasname):
        raise PageExistsError(courseobj, canvastitle)

    return __create_page(courseobj, canvastitle)

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

def __record_push(filename, pageobj):
    with open(__tpp_path(filename), "w") as fh:
        toml.dump(__page_metadata(filename, pageobj), fh)

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
    together are both reported, not just whichever is checked first.

    Uses __find_page rather than __resolve_page: a page that no longer
    exists at all (deleted independently of tent-pole -- confirmed
    live during an integration-test course reset) is reported as its
    own drift problem here rather than raising, so a caller like
    `verify` still learns about it instead of crashing outright. push
    needs the raise-free __find_page result itself, checked before
    ever calling this, to decide whether there is anything live left
    to protect against overwriting at all."""
    canvasname = canvasname_from_path(filename)
    pageobj = __find_page(course.course_obj(), canvasname)
    if pageobj is None:
        return ["page no longer exists on Canvas"]

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
    pageobj = __resolve_page(course.course_obj(), canvasname)
    __record_push(filename, pageobj)

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
    courseobj = course.course_obj()
    page = __resolve_page(courseobj, canvasname_from_path(filename))
    page.edit(
        wiki_page={
            "body":body
        }
    )

@page.command(help="Create or Update a page")
@click.argument("filename")
@click.option("--force", is_flag=True, help="Push even if the remote "
              "page has drifted since the last push/dump (someone "
              "else edited it since, or its content no longer matches "
              "what tent-pole last saw there).")
def push(filename, force):
    with open(filename) as fh: body = fh.read()
    courseobj = course.course_obj()
    canvasname = canvasname_from_path(filename)

    ## Only a page pushed before, that still actually exists, has a
    ## baseline worth drift-checking -- a first-ever push has nothing
    ## to compare against, and a page deleted independently of
    ## tent-pole (confirmed live during an integration-test course
    ## reset) has nothing live left to protect against overwriting, so
    ## just recreate it below rather than crashing on "no page found"
    ## from inside what should be an optional safety check.
    if (
        not force
        and os.path.exists(__tpp_path(filename))
        and __find_page(courseobj, canvasname) is not None
    ):
        problems = __remote_drift(filename, __load_tpp(filename))
        if problems:
            raise click.ClickException(
                "; ".join(problems) + " -- use --force to overwrite anyway"
            )

    page = __get_create_page(courseobj, canvasname)
    page.edit (
        wiki_page = {
            "body": body
        }
    )
    ## Recorded immediately, not left to a separate `dump` step: a
    ## transient failure between the two (e.g. Canvas returning a
    ## flaky 502 while the edit itself still went through, or the
    ## build's own recursive fan-out aborting for an unrelated page in
    ## between) would otherwise leave the live push permanently
    ## unrecorded, so every retry re-trips __compiled_at_drift against
    ## tent-pole's own prior successful push -- confirmed live against
    ## the CSC1034 integration sandbox, see quiz.py's push/__dump_tpq
    ## for the same pattern already in place there.
    __record_push(filename, page)
    print("Pushed:{} as {}".format(filename, page.url))
    if page.url != canvasname:
        print("  {!r} was already taken, landed on {!r} instead".format(
            canvasname, page.url
        ))
