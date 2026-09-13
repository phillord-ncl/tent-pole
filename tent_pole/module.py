import canvasapi
import click
import toml

from . import config
from . import course
from . import manifest
from . import page
from . import quiz

def module_by_name(modulename):
    try:
        return next(module for module
                in course.course_obj().get_modules()
                if modulename in getattr(module, "name", ""))
    except StopIteration:
        return None

def module_by_guess(moduleidentifier):
    if moduleidentifier.isnumeric():
        try:
            return course.course_obj().get_module(moduleidentifier)
        except canvasapi.exceptions.ResourceDoesNotExist:
            pass
    return module_by_name(moduleidentifier)

def module_obj():
    return module_by_guess(config.config_module())

def __get_or_create_module(modulename, courseobj):
    """Return (module, created) for the course's module named
    `modulename` -- exact match, not module_by_name's substring search,
    so e.g. "Week 1" is never satisfied by an existing "Week 10".
    Creates it if none exists yet."""
    existing = next((m for m in courseobj.get_modules() if m.name == modulename), None)
    if existing is not None:
        return existing, False
    return courseobj.create_module({"name": modulename}), True

def __desired_module_item(item, position, courseobj):
    """(identity key, module_item dict) for one tent-pole.toml
    [module] items entry, or (None, None) for an item type reorder()
    doesn't know how to build -- silently skipped, same as before this
    was rewritten. The identity key is what a live Canvas module item
    is matched against, in __live_item_key below."""
    itemtype = item.get("type", "Page")
    indent = str(item.get("indent", 0))
    if itemtype == "Page":
        canvasname = page.canvasname_from_path(item["id"])
        ## The page's real url, not the assumed canvasname -- Canvas
        ## reserves a deleted page's slug for undelete, so a page
        ## that's ever been deleted and recreated can live at a
        ## different url (comprehensions-and-operations-2, etc) than
        ## its filename would suggest. Falls back to canvasname if the
        ## page doesn't exist yet at all; Canvas will reject that with
        ## its own clear error rather than silently misaddressing it.
        found = page.__find_page(courseobj, canvasname)
        page_url = found.url if found is not None else canvasname
        return ("Page", page_url), {
            "type": "Page", "page_url": page_url,
            "indent": indent, "position": position,
        }
    if itemtype == "Quiz":
        ## item["id"] is a .quiz.md filename, matching how "Page"
        ## above already takes a filename rather than a raw Canvas id
        ## -- resolved via its .tpq (quiz push's own stamp file), the
        ## same way a Page item resolves via .tpp/__find_page. Unlike
        ## Page, there's no meaningful guessed fallback for a numeric
        ## content_id when unpushed, so this errors instead of
        ## silently misaddressing -- reorder should never implicitly
        ## create a quiz.
        recorded = quiz.__load_tpq(item["id"])
        if recorded is None:
            raise click.ClickException(
                "No {} found for {!r} -- run quiz push first".format(
                    quiz.__tpq_path(item["id"]), item["id"]
                )
            )
        content_id = recorded["quiz_id"]
        return ("Quiz", content_id), {
            "type": "Quiz", "content_id": content_id,
            "indent": indent, "position": position,
        }
    return None, None

def __live_item_key(liveitem):
    itemtype = getattr(liveitem, "type", None)
    if itemtype == "Page":
        return ("Page", getattr(liveitem, "page_url", None))
    if itemtype == "Quiz":
        return ("Quiz", getattr(liveitem, "content_id", None))
    return (itemtype, getattr(liveitem, "id", None))

def __live_item_matches_desired(liveitem, desired):
    return (
        str(getattr(liveitem, "position", None)) == str(desired["position"])
        and str(getattr(liveitem, "indent", "0")) == desired["indent"]
    )

## CLI
@click.group()
def module():
    pass

@module.command(help="Return some information about a module")
@click.argument("moduleidentifier")
def data(moduleidentifier):
    module = module_by_guess(moduleidentifier)
    print(module)

@module.command(help="Return list of items in a module")
@click.argument("moduleidentifier")
def list(moduleidentifier):
    module = module_by_guess(moduleidentifier)
    for i, item in enumerate(module.get_module_items()):
        print(i+1, ":", item)

# should be at course level?
@module.command(help="Delete a module form the course")
@click.argument("moduleidentifier")
def delete(moduleidentifier):
    module = module_by_guess(moduleidentifier)
    if (module):
        print("Are you certain you want to delete module", module, "? [N/y]")
        choice = input().strip()
        if (choice == "y" or choice == "Y"):
            module.delete()
            print("Deleted module:", module)
        else:
            print("Module", moduleidentifier, "not deleted")
    else:
        print("Error: Module", moduleidentifier, "not found")

# should be at course level?
@module.command(help="Create a module for a course, unless one with that name already exists")
@click.argument("modulename", required=False)
def create(modulename):
    modulename = modulename or config.config_module()
    courseobj = course.course_obj()

    _, created = __get_or_create_module(modulename, courseobj)
    if created:
        print("Created module:", modulename)
    else:
        print("Module already exists:", modulename)

@module.command(help="Adds a page to a module")
@click.argument("moduleidentifier")
@click.argument("pageurl")
@click.argument("indent", default=0)
def addpage(moduleidentifier, pageurl, indent=0):
    module = module_by_guess(moduleidentifier)
    if (module):
        item = page.page_by_guess(pageurl)
        if (item):
            module.create_module_item({"type": "Page", "page_url": pageurl, "indent":indent})
            print("Added page", pageurl, "to module", moduleidentifier)
        else:
            print("Error: Page", pageurl, "not found")
    else:
        print("Error: Module", moduleidentifier, "not found")

@module.command(help="Adds a sub header to a module")
@click.argument("moduleidentifier")
@click.argument("headtitle")
@click.argument("indent", default=0)
def addhead(moduleidentifier, headtitle, indent=0):
    module = module_by_guess(moduleidentifier)
    if (module):
        module.create_module_item({"type": "SubHeader", "title": headtitle, "indent": indent})
        print("Added sub header", headtitle, "to module", moduleidentifier)
    else:
        print("Error: Module", moduleidentifier, "not found")

@module.command(help="Adds a file to a module")
@click.argument("moduleidentifier")
@click.argument("fileidentifier")
@click.argument("indent", default=0)
def addfile(moduleidentifier, fileidentifier, indent=0):
    module = module_by_guess(moduleidentifier)
    if (module):
        module.create_module_item({"type": "File", "content_id": fileidentifier, "indent":indent})
        print("Added file", fileidentifier, "to module", moduleidentifier)
    else:
        print("Error: Module", moduleidentifier, "not found")

@module.command(help="Create the module if needed, then bring its item "
                      "list in line with tent-pole.toml -- editing "
                      "position/indent in place for an item that's "
                      "already there, rather than deleting and "
                      "recreating everything (which would reset any "
                      "student completion state tracked against the "
                      "item's id).")
def reorder():
    modulename = config.config_module()
    courseobj = course.course_obj()
    mod, created = __get_or_create_module(modulename, courseobj)
    if created:
        print("Created module:", modulename)

    required_items = config.config_module_items()
    ## Not list(...) -- the "list" CLI command defined above rebinds
    ## the module-level name "list" to itself, shadowing the builtin.
    live_items = [item for item in mod.get_module_items()]
    live_by_key = {}
    for liveitem in live_items:
        live_by_key.setdefault(__live_item_key(liveitem), []).append(liveitem)

    matched_ids = set()
    for position, item in enumerate(required_items, start=1):
        key, desired = __desired_module_item(item, position, courseobj)
        if key is None:
            continue

        candidates = live_by_key.get(key)
        liveitem = candidates.pop(0) if candidates else None
        if liveitem is None:
            print("Adding {} to module: {}".format(desired["type"], item.get("id")))
            mod.create_module_item(module_item=desired)
            continue

        matched_ids.add(liveitem.id)
        if not __live_item_matches_desired(liveitem, desired):
            liveitem.edit(module_item=desired)

    for liveitem in live_items:
        if liveitem.id not in matched_ids:
            liveitem.delete()

@module.command(help="Dump the module's resolved state to stdout as TOML.")
def dump():
    modulename = config.config_module()
    courseobj = course.course_obj()
    mod = next((m for m in courseobj.get_modules() if m.name == modulename), None)
    if mod is None:
        raise click.ClickException(
            "Module {!r} not found -- run reorder first".format(modulename)
        )

    required_items = config.config_module_items()
    data = {
        "module_id": mod.id,
        "name": mod.name,
        "hash": manifest.hash_bytes(toml.dumps({"items": required_items}).encode()),
    }
    print(toml.dumps(data))
