import click

from . import config
from . import course
from . import page

def module_by_name(modulename):
    try:
        return next(module for module
                in course.course_obj().get_modules()
                if modulename in module.name)
    except:
        return None

def module_by_guess(moduleidentifier):
    print(config.config_course())
    return (
        moduleidentifier.isnumeric()
        and
        config.config_canvas().get_course(config.config_course()).get_module(moduleidentifier)
        or
        module_by_name(moduleidentifier)
    )

def module_obj():
    return module_by_guess(config.config_module())

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
@module.command(help="Create a module for a course")
@click.argument("modulename")
def create(modulename):
    course = config.config_canvas().get_course(config.config_course())
    course.create_module({"name":modulename})
    print("Created module:", modulename)

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

# Not tested
@module.command(help="Reorder the Module")
def reorder():
    module = module_obj()
    required_items = config.config_module_items()

    for item in module.get_module_items():
        item.delete()

    for item in required_items:
        itemtype = item.get("type", "Page")
        if itemtype=="Page":
            print("Creating page")
            print(page.canvasname_from_path(item['id']))
            module.create_module_item(
                module_item = {
                    "type": "Page",
                    "page_url": page.canvasname_from_path(item['id']),
                    "indent": str(item.get("indent", 0))
                }
            )
        elif itemtype=="Quiz":
                module.create_module_item(
                    module_item = {
                        "type": "Quiz",
                        "content_id": item['id'],
                        "indent": item.get("indent", 0)
                    }
                )
