import click

from . import config
from . import course
from . import page

def module_by_name(modulename):
    return next(module for module
                in course.course_obj().get_modules()
                if modulename in module.name)

def module_by_guess(moduleidentifier):
    return (
        moduleidentifier.isnumeric()
        and
        config.config_canvas_obj().get_module(moduleidentifier)
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
    print(module.__dict__)

@module.command(help="Return list of items")
def list():
    module = module_obj()
    for m in module.get_module_items():
        print(m.__dict__)

@module.command(help="Reorder the Module")
def reorder():
    module = module_obj()
    required_items = config.config_module_items()

    for item in module.get_module_items():
        item.delete()

    for item in required_items:
        itemtype = item.get("type", "Page")
        if itemtype=="Page":
            module.create_module_item(
                module_item = {
                    "type": "Page",
                    "page_url": page.canvasname_from_path(item['id']),
                    "indent": item.get("indent", 0)
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
