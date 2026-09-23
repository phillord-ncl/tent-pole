import os
import re

import click

from . import course
from . import course_import_filter
from . import scaffold

SLUG_PATTERN = re.compile(r'[^a-z0-9]+')


def __slugify(name):
    return SLUG_PATTERN.sub("-", name.lower()).strip("-") or "module"


def __unique_name(name, used):
    candidate = name
    n = 1
    while candidate in used:
        n += 1
        candidate = "{}-{}".format(name, n)
    used.add(candidate)
    return candidate


def __toml_string(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def __course_toml(course_id):
    return '[course]\nid = "{}"\n'.format(__toml_string(str(course_id)))


def __module_toml(identifier, items):
    lines = ['[module]', 'identifier = "{}"'.format(__toml_string(identifier)), 'items = [']
    for item in items:
        parts = ['id="{}"'.format(__toml_string(item["id"]))]
        if item.get("indent"):
            parts.append("indent={}".format(item["indent"]))
        lines.append("  {{{}}},".format(", ".join(parts)))
    lines.append(']')
    return "\n".join(lines) + "\n"


def __notice(kind, label, modulename):
    click.echo("Not imported: {} {!r} in module {!r}".format(kind, label, modulename))


def __module_page_items(courseobj, modules):
    """(page_items_by_module, module_for_page_url) -- page_items_by_module
    maps each Module to its own Page-type items only, sorted by live
    Canvas position; module_for_page_url maps a page's url to the module
    it belongs to, for every page that belongs to one. Non-Page items
    (Quiz, SubHeader, Assignment, ...) are reported via __notice, per
    course_import's read-only/no-silent-drops scope, and otherwise
    ignored -- there is nothing to write for them."""
    page_items_by_module = {}
    module_for_page_url = {}

    for module in modules:
        items = list(module.get_module_items())
        page_items = sorted(
            (i for i in items if getattr(i, "type", None) == "Page"),
            key=lambda i: getattr(i, "position", 0) or 0,
        )
        page_items_by_module[module] = page_items

        for item in items:
            itemtype = getattr(item, "type", None)
            if itemtype == "Page":
                module_for_page_url[getattr(item, "page_url", None)] = module
            else:
                label = getattr(item, "title", None) or getattr(item, "content_id", None)
                __notice(itemtype, label, module.name)

    return page_items_by_module, module_for_page_url


def __write_module(directory, dirname, module, page_items):
    moddir = os.path.join(directory, dirname)
    os.makedirs(moddir, exist_ok=True)
    items = [
        {"id": getattr(item, "page_url", None), "indent": getattr(item, "indent", 0)}
        for item in page_items
    ]
    with open(os.path.join(moddir, "tent-pole.toml"), "w") as fh:
        fh.write(__module_toml(module.name, items))
    return moddir


def __write_page(courseobj, page_url, target_dir, page_slugs, contexts):
    real_page = courseobj.get_page(page_url)
    context = contexts.get(target_dir)
    if context is None:
        context = course_import_filter.ImportContext(courseobj, page_slugs, target_dir)
        contexts[target_dir] = context

    markdown = course_import_filter.convert(real_page.body or "", context)
    with open(os.path.join(target_dir, page_url + ".md"), "w") as fh:
        fh.write(markdown)


def run_import(courseidentifier, directory, no_git):
    courseobj = course.course_by_guess(courseidentifier)
    if courseobj is None:
        raise click.ClickException("No course found for {!r}".format(courseidentifier))

    directory = directory or __slugify(getattr(courseobj, "name", str(courseidentifier)))
    if os.path.exists(directory) and os.listdir(directory):
        raise click.ClickException(
            "{} already exists and is not empty".format(directory)
        )
    os.makedirs(directory, exist_ok=True)

    modules = list(courseobj.get_modules())
    pages = list(courseobj.get_pages())
    page_slugs = [p.url for p in pages]

    page_items_by_module, module_for_page_url = __module_page_items(courseobj, modules)

    used_dirnames = set()
    dirname_by_module = {}
    for module in modules:
        page_items = page_items_by_module[module]
        if not page_items:
            continue
        dirname = __unique_name(__slugify(module.name), used_dirnames)
        dirname_by_module[module] = dirname
        __write_module(directory, dirname, module, page_items)

    contexts = {}
    for p in pages:
        module = module_for_page_url.get(p.url)
        dirname = dirname_by_module.get(module) if module is not None else None
        target_dir = os.path.join(directory, dirname) if dirname else directory
        __write_page(courseobj, p.url, target_dir, page_slugs, contexts)

    with open(os.path.join(directory, "tent-pole.toml"), "w") as fh:
        fh.write(__course_toml(courseobj.id))

    if not no_git:
        cwd = os.getcwd()
        os.chdir(directory)
        try:
            scaffold.git_init_unless_already_in_repo()
        finally:
            os.chdir(cwd)

    click.echo("Imported {} into {}".format(courseidentifier, directory))


@click.command(name="import", help="Pull an existing Canvas course down "
               "to a local tent-pole project: pages as best-effort "
               "markdown, their images/files, and module structure, "
               "scaffolded like `tent-pole init`. Strictly read-only "
               "against Canvas. Quizzes and other non-page module "
               "items are listed as not imported, never silently "
               "dropped -- see docs/import-a-course.md.")
@click.argument("courseidentifier")
@click.argument("directory", required=False)
@click.option("--no-git", is_flag=True, help="Don't run git init.")
def import_command(courseidentifier, directory, no_git):
    run_import(courseidentifier, directory, no_git)
