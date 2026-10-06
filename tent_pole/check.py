import glob
import os

import click
import toml

from . import include_deps_filter
from . import page


def _module_tomls(root):
    """(directory, module_dict) for every tent-pole.toml under root whose
    own section is [module], not [course] or a bare top-level config --
    only a [module] directory's *.md files are pages the normal build
    would ever push, so a [course] directory (e.g. a lecture-slide
    source tree) must never be treated as a page source here."""
    for toml_path in sorted(glob.glob(os.path.join(root, "**", "tent-pole.toml"), recursive=True)):
        with open(toml_path) as fh:
            data = toml.load(fh)
        module = data.get("module")
        if module is not None:
            yield os.path.dirname(toml_path), module


def _md_sources(directory):
    return sorted(
        md for md in glob.glob(os.path.join(directory, "*.md"))
        if not md.endswith(".quiz.md")
    )


def _tpf_deps(md):
    """Local files `md`'s own page would push via task_tpf (images,
    include=/output=/stout=/crash=/plot=, local-asset links) -- mirrors
    core.py's task_tpf exactly (html_deps entries that end in .tpf name
    the file to push, with that suffix stripped). parse() only ever
    extracts path strings from the AST, never opens the files they name,
    so unlike a real pandoc --filter run this needs no cwd juggling to
    match the directory the paths are written relative to."""
    html_deps, _ = include_deps_filter.parse(md)
    directory = os.path.dirname(md)
    for dep in html_deps:
        if dep.endswith(".tpf"):
            yield os.path.normpath(os.path.join(directory, dep[: -len(".tpf")]))


def name_collision(root="."):
    """Pages and task_tpf-pushed files that would land on the same
    Canvas identity (canvasname/filename) purely because of shared
    basenames -- computed from what's on disk alone, regardless of
    whether anything has actually been pushed yet. Catches a collision
    before the first push, but can't tell a real duplicate from two
    files that happen to share a name and were never going to collide
    for some other reason -- see stamp_collision for the confirmed
    version of this."""
    findings = []

    by_pagename = {}
    by_filename = {}
    for directory, _ in _module_tomls(root):
        for md in _md_sources(directory):
            by_pagename.setdefault(page.canvasname_from_path(md), []).append(md)
            for dep in _tpf_deps(md):
                by_filename.setdefault(os.path.basename(dep), []).append(dep)

    for name, paths in sorted(by_pagename.items()):
        distinct = sorted(set(paths))
        if len(distinct) > 1:
            findings.append("page {!r} claimed by: {}".format(name, ", ".join(distinct)))

    for name, paths in sorted(by_filename.items()):
        distinct = sorted(set(paths))
        if len(distinct) > 1:
            findings.append("file {!r} claimed by: {}".format(name, ", ".join(distinct)))

    return findings


def _stamp_group(root, pattern, identity_keys):
    by_identity = {}
    for stamp_path in sorted(glob.glob(os.path.join(root, "**", pattern), recursive=True)):
        with open(stamp_path) as fh:
            data = toml.load(fh)
        identity = next((data.get(key) for key in identity_keys if data.get(key)), None)
        if identity is None:
            continue
        by_identity.setdefault(identity, []).append(stamp_path)
    return by_identity


def stamp_collision(root="."):
    """.tpp/.tpf stamps that record the same live Canvas identity
    (page url/id, file filename/id) under more than one source path --
    definitive, not inferred: two distinct local files only ever record
    the same identity if a push actually landed them on the same
    Canvas object, e.g. one silently overwriting the other."""
    findings = []

    by_page = _stamp_group(root, "*.tpp", ("url", "page_id"))
    for identity, paths in sorted(by_page.items(), key=lambda kv: str(kv[0])):
        distinct = sorted(set(paths))
        if len(distinct) > 1:
            findings.append("page {!r} claimed by: {}".format(identity, ", ".join(distinct)))

    by_file = _stamp_group(root, "*.tpf", ("filename", "id"))
    for identity, paths in sorted(by_file.items(), key=lambda kv: str(kv[0])):
        distinct = sorted(set(paths))
        if len(distinct) > 1:
            findings.append("file {!r} claimed by: {}".format(identity, ", ".join(distinct)))

    return findings


def unreferenced(root="."):
    """A [module] directory's *.md that the normal build would push as
    a page (task_page_push globs every *.md unconditionally) but that
    directory's own tent-pole.toml items never mentions -- a page that
    exists on Canvas but never shows up in the module's own navigation."""
    findings = []
    for directory, module in _module_tomls(root):
        ## module.py's own resolution (__desired_module_item) runs
        ## item["id"] through canvasname_from_path too -- an id is a
        ## raw filename stem (often underscored), not already a
        ## canvasname, so comparing it as-is against name below would
        ## false-positive on every underscored id.
        item_ids = {
            page.canvasname_from_path(item["id"]) for item in module.get("items", [])
        }
        for md in _md_sources(directory):
            name = page.canvasname_from_path(md)
            if name not in item_ids:
                findings.append(
                    "{} (page {!r}) is not in any [module] item of {}".format(
                        md, name, os.path.join(directory, "tent-pole.toml")
                    )
                )
    return findings


LINTERS = {
    "name-collision": name_collision,
    "stamp-collision": stamp_collision,
    "unreferenced": unreferenced,
}

## "build": only name-collision needs no prior push state at all, so
## it's the one linter a single invocation at the course root can run
## correctly before anything has ever been pushed -- stamp-collision
## only has anything to say about a page/file that's already been
## pushed at least once, and unreferenced is an authoring-hygiene lint,
## not a collision gate.
ALIASES = {
    "all": tuple(sorted(LINTERS)),
    "build": ("name-collision",),
}


def _resolve(names):
    resolved = []
    for name in names:
        resolved.extend(ALIASES.get(name, (name,)))
    return list(dict.fromkeys(resolved))


@click.command(help="Run static checks for common authoring mistakes: "
                     "page/file name collisions (name-collision, "
                     "stamp-collision) and pages missing from their own "
                     "module's item list (unreferenced). 'all' runs every "
                     "linter; 'build' runs the subset safe to wire into a "
                     "build (currently just name-collision). Always run "
                     "from the course root -- these walk the whole tree, "
                     "not just the current directory.")
@click.argument("linters", nargs=-1, required=True,
                 type=click.Choice(sorted(LINTERS) + sorted(ALIASES)))
@click.option("--strict", is_flag=True, help="Exit non-zero if any "
              "linter reports a finding, instead of just printing them.")
def check(linters, strict):
    findings = [
        "[{}] {}".format(name, finding)
        for name in _resolve(linters)
        for finding in LINTERS[name](".")
    ]

    for finding in findings:
        print(finding)
    if not findings:
        print("OK: no issues found ({})".format(", ".join(linters)))

    if strict and findings:
        raise click.ClickException("{} issue(s) found".format(len(findings)))
